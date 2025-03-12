import numpy as np
from matplotlib.backend_tools import Cursors
from matplotlib.widgets import AxesWidget


class Ruler(AxesWidget):
    """
    A ruler to measure distances and angles on an axes instance.

    For the ruler to remain responsive you must keep a reference to it.

    Parameters
    ----------
    ax  : the  :class:`matplotlib.axes.Axes` instance

    active : bool, default is False
        Whether the ruler is active or not.

    length_fmt  : string, A format string used in displayed text for lengths
        i.e. ('{0}ft', or '{0:0.1f}m')

    angle_fmt  : string, A format string used in displayed text for angles
        i.e. ('{0}deg', or '{0:0.2f}rad')

    angle_in_degrees  : bool, default is True
        Whether to use degrees or radians for the angle measurement

    print_text  : bool, default is False
        Whether the length measure string is printed to the console

    useblit : bool, default is False
        If True, use the backend-dependent blitting features for faster
        canvas updates.

    lineprops : dict, default is None
      Dictionary of :class:`matplotlib.lines.Line2D` properties

    markerprops : dict, default is None
      Dictionary of :class:`matplotlib.markers.MarkerStyle` properties

    textprops: dict, default is None
        Dictionary of :class:`matplotlib.text.Text` properties. To reposition the
        textbox you can overide the defaults which position the box in the top left
        corner of the axes.

    Usage:
    ----------

    1. Hold left click drag and release to draw the ruler in the axes.
      - Hold shift while dragging to lock the ruler to the horizontal axis.
      - Hold control while drawing to lock the ruler to the vertical axis.

    2. Right click one of the markers to move the ruler.

    The keyboard can be used to activate and deactivate the ruler and toggle
    visibility of the line and text:

    'm' : Toggles the ruler on and off.

    'ctl+m' : Toggles the visibility of the ruler and text.

    Example
    ----------

    >>> xCoord = np.arange(0, 5, 1)
    >>> yCoord = [0, 1, -3, 5, -3]
    >>> fig = plt.figure()
    >>> ax = fig.add_subplot(111)

    >>> markerprops = dict(marker='o', markersize=5, markeredgecolor='red')
    >>> lineprops = dict(color='red', linewidth=2)

    >>> ax.grid(True)
    >>> ax.plot(xCoord, yCoord)

    >>> ruler = Ruler(ax=ax,
                  useblit=True,
                  markerprops=markerprops,
                  lineprops=lineprops)

    >>> plt.show()

    """

    def __init__(
        self,
        ax,
        active=False,
        length_fmt="{0:0.3f}",
        angle_fmt="{0:0.2f}deg",
        angle_in_degrees=True,
        print_text=False,
        useblit=False,
        lineprops=None,
        textprops=None,
        markerprops=None,
    ):
        """
        Add a ruler to *ax*. If ``active=True``, the ruler will be
        activated when the plot is first created.
        """
        AxesWidget.__init__(self, ax)

        self.connect_events()

        self.ax = ax
        self.fig = ax.figure

        self._print_text = print_text
        self._visible = True
        self.active = active
        self.length_fmt = length_fmt
        self.angle_fmt = angle_fmt
        self.angle_in_degrees = angle_in_degrees
        self.useblit = useblit and self.canvas.supports_blit

        self._ruler_drawing = False
        self._pressed_keys = []
        self._mouse_buttons = set()
        self._x0 = None
        self._y0 = None
        self._x1 = None
        self._y1 = None
        self._line_start_coords = None
        self._line_end_coords = None
        self._ruler_marker = None
        self._background = None
        self._ruler_moving = False
        self._end_a_lock = False
        self._end_b_lock = False
        self._end_c_lock = False
        self._old_marker_a_coords = None
        self._old_marker_c_coords = None
        self._old_mid_coords = None

        if lineprops is None:
            lineprops = {}

        bbox = dict(facecolor="white", alpha=0.5, boxstyle="round", edgecolor="0.75")

        used_textprops = dict(
            xy=(0, 1),
            xytext=(10, -10),
            xycoords="axes fraction",
            textcoords="offset points",
            ha="left",
            va="center",
            bbox=bbox,
        )

        x0 = np.nan
        y0 = np.nan

        (self._ruler,) = self.ax.plot([x0, x0], [y0, y0], **lineprops)

        used_markerprops = dict(
            marker="s",
            markersize=3,
            markerfacecolor="white",
            markeredgecolor="black",
            markeredgewidth=0.5,
            picker=5,
            visible=False,
        )

        # If marker or text  props are given as an argument combine with the
        # default marker props. Don't really want to override the entire props
        # if a user only gives one value.

        if markerprops is not None:
            used_markerprops.update(markerprops)

        if textprops is not None:
            used_textprops.update(used_textprops)

        self._axes_text = self.ax.annotate(text="", **used_textprops)
        self.ax.add_artist(self._axes_text)

        (self._marker_a,) = self.ax.plot((x0, y0), **used_markerprops)
        (self._marker_b,) = self.ax.plot((x0, y0), **used_markerprops)
        (self._marker_c,) = self.ax.plot((x0, y0), **used_markerprops)

        self._artists = [
            self._axes_text,
            self._ruler,
            self._marker_a,
            self._marker_b,
            self._marker_c,
        ]

    @property
    def _mouse1_pressed(self):
        return 1 in self._mouse_buttons

    @property
    def _control_pressed(self):
        return any(e in self._pressed_keys for e in ("ctrl", "control"))

    @property
    def _shift_pressed(self):
        return "shift" in self._pressed_keys

    def connect_events(self):
        """
        Connect all events to the various callbacks
        """
        self.connect_event("button_press_event", self._on_press)
        self.connect_event("button_release_event", self._on_release)
        self.connect_event("motion_notify_event", self._on_move)
        self.connect_event("key_press_event", self._on_key_press)
        self.connect_event("key_release_event", self._on_key_release)

    def ignore(self, event):
        """
        Ignore events if the cursor is out of the axes or the widget is locked
        """
        if self.fig.canvas.toolbar.mode:
            return True
        if not self.canvas.widgetlock.available(self):
            return True
        if event.inaxes != self.ax.axes:
            return True
        if not self.active:
            return True
        if not self._visible:
            return True
        return False

    def _on_key_press(self, event):
        """
        Handle key press events.

        If shift is pressed the ruler will be constrained to horizontal axis
        If control is pressed the ruler will be constrained to vertical axis
        If m is pressed the ruler will be toggled on and off
        If ctrl+m is pressed the visibility of the ruler will be toggled
        """

        self._pressed_keys = event.key.split("+") if event.key else []
        self._update_cursor(event)

        if event.key == "m":
            self.toggle_ruler()
        elif event.key == "ctrl+m":
            self.toggle_ruler_visibility()

    def _on_key_release(self, event):
        """
        Handle key release event, flip the flags to false.
        """

        for key in event.key.split("+"):
            if key in self._pressed_keys:
                self._pressed_keys.remove(key)
        self._update_cursor(event)

    def toggle_ruler(self):
        """
        Called when the 'm' key is pressed. If ruler is on turn it off, and
        vise versa
        """

        self.active = not self.active

    def toggle_ruler_visibility(self):
        """
        Called when the 'ctl+m' key is pressed. If ruler is visible turn it off
        , and vise versa
        """
        if self._visible:
            for artist in self._artists:
                artist.set_visible(False)
            self.active = False
            self._visible = False

        elif self._visible is False:
            for artist in self._artists:
                artist.set_visible(True)
            self._visible = True

        self._update_text()
        self._update_artists()

    def _on_press(self, event):
        """
        On mouse button press check which button has been pressed and handle
        """
        self._pressed_keys = event.key.split("+") if event.key else []
        self._mouse_buttons.add(event.button)

        if self.ignore(event):
            return

        if event.button == 1:
            if any(self._over_marker(event)):
                self._handle_ruler_move(event)
            else:
                self._handle_ruler_draw(event)

    def _over_marker(self, event):
        contains_a, _ = self._marker_a.contains(event)
        contains_b, _ = self._marker_b.contains(event)
        contains_c, _ = self._marker_c.contains(event)

        return contains_a, contains_b, contains_c

    def _handle_ruler_move(self, event):
        """
        If button 3 is pressed (right click) check if cursor is at one of the
        ruler markers and the move the ruler accordingly.
        """
        contains_a, contains_b, contains_c = self._over_marker(event)

        if not (contains_a or contains_b or contains_c):
            return

        self._end_a_lock = contains_a
        self._end_b_lock = contains_b
        self._end_c_lock = contains_c

        line_coords = self._ruler.get_path().vertices
        self._x0 = line_coords[0][0]
        self._y0 = line_coords[0][1]
        self._x1 = line_coords[1][0]
        self._y1 = line_coords[1][1]

        self._old_marker_a_coords = self._marker_a.get_path().vertices
        self._old_marker_c_coords = self._marker_c.get_path().vertices
        self._old_mid_coords = self.midline_coords

    def _handle_ruler_draw(self, event):
        """
        On button 1 press start drawing the ruler line from the initial
        press position
        """
        self._ruler_drawing = True
        self._x0 = event.xdata
        self._y0 = event.ydata
        self._marker_a.set_data([event.xdata], [event.ydata])
        self._marker_a.set_visible(True)

        if self.useblit:
            self._marker_a.set_data([self._x0], [self._y0])
            for artist in self._artists:
                artist.set_animated(True)
            self.canvas.draw()
            self._background = self.canvas.copy_from_bbox(self.fig.bbox)

    def _on_move(self, event):
        """
        On motion draw the ruler if button 1 is pressed. If one of the markers
        is locked indicating move the ruler according to the locked marker
        """

        self._pressed_keys = event.key.split("+") if event.key else []
        self._update_cursor(event)

        if event.inaxes != self.ax.axes:
            return

        if self._end_a_lock or self._end_b_lock or self._end_c_lock:
            self._move_ruler(event)
        elif self._ruler_drawing:
            self._draw_ruler(event)

    def _move_ruler(self, event):
        """
        If one of the markers is locked move the ruler according the selected
        marker.
        """

        # This flag is used to prevent the ruler from clipping when a marker is
        # first selected
        if self._ruler_moving is False:
            if self.useblit:
                for artist in self._artists:
                    artist.set_animated(True)
                self.canvas.draw()
                self._background = self.canvas.copy_from_bbox(self.fig.bbox)
                self._ruler_moving = True

        if self._end_a_lock:
            # If marker c is locked only move end a.

            # If shift is pressed ruler is constrained to horizontal axis
            if "shift" in self._pressed_keys:
                pos_a = event.xdata, self._x1
                pos_b = self._y0, self._y1
            # If control is pressed ruler is constrained to vertical axis
            elif self._control_pressed:
                pos_a = self._x0, self._x1
                pos_b = event.ydata, self._y1
            # Else the ruler follow the mouse cursor
            else:
                pos_a = event.xdata, self._x1
                pos_b = event.ydata, self._y1

            self._marker_a.set_data(pos_a[:1], pos_b[:1])
            self._ruler.set_data(pos_a, pos_b)
            self._set_midline_marker()

        if self._end_c_lock:
            # If marker a is locked only move end c.

            # If shift is pressed ruler is constrained to horizontal axis
            if self._shift_pressed:
                pos_a = self._x0, event.xdata
                pos_b = self._y0, self._y1
            # If control is pressed ruler is constrained to vertical axis
            elif self._control_pressed:
                pos_a = self._x0, self._x1
                pos_b = self._y0, event.ydata
            # Else the ruler follow the mouse cursor
            else:
                pos_a = self._x0, event.xdata
                pos_b = self._y0, event.ydata

            self._marker_c.set_data(pos_a[1:2], pos_b[1:2])
            self._ruler.set_data(pos_a, pos_b)
            self._set_midline_marker()

        if self._end_b_lock:
            # If marker b is locked shift the whole ruler.
            b_dx = event.xdata - self._old_mid_coords[0]
            b_dy = event.ydata - self._old_mid_coords[1]

            # If shift is pressed ruler is constrained to horizontal axis
            if self._shift_pressed:
                b_dy = 0
            # If control is pressed ruler is constrained to vertical axis
            elif self._control_pressed:
                b_dx = 0

            pos_a = self._x0 + b_dx, self._x1 + b_dx
            pos_b = self._y0 + b_dy, self._y1 + b_dy
            pos_c = self._old_mid_coords[0] + b_dx, self._old_mid_coords[1] + b_dy

            self._ruler.set_data(pos_a, pos_b)
            self._marker_a.set_data(
                [self._old_marker_a_coords[0][0] + b_dx],
                [self._old_marker_a_coords[0][1] + b_dy],
            )
            self._marker_b.set_data(*[[e] for e in pos_c])
            self._marker_c.set_data(
                [self._old_marker_c_coords[0][0] + b_dx],
                [self._old_marker_c_coords[0][1] + b_dy],
            )

        self._update_text()
        self._update_artists()

    def _set_midline_marker(self):
        self._marker_b.set_visible(True)
        self._marker_b.set_data(*[[e] for e in self.midline_coords])

    @property
    def midline_coords(self):
        pos0, pos1 = self._ruler.get_path().vertices
        return (pos0[0] + pos1[0]) / 2, (pos0[1] + pos1[1]) / 2

    def _draw_ruler(self, event):
        """
        If the left mouse button is pressed and held draw the ruler as the
        mouse is dragged
        """

        self._x1 = event.xdata
        self._y1 = event.ydata

        # If shift is pressed ruler is constrained to horizontal axis
        if self._shift_pressed:
            pos_a = self._x0, self._x1
            pos_b = self._y0, self._y0
        # If control is pressed ruler is constrained to vertical axis
        elif self._control_pressed:
            pos_a = self._x0, self._x0
            pos_b = self._y0, self._y1
        # Else the ruler follow the mouse cursor
        else:
            pos_a = self._x0, self._x1
            pos_b = self._y0, self._y1

        self._ruler.set_data([pos_a], [pos_b])
        x1 = self._ruler.get_path().vertices[1][0]
        y1 = self._ruler.get_path().vertices[1][1]
        self._marker_c.set_visible(True)
        self._marker_c.set_data([x1], [y1])
        self._set_midline_marker()
        self._update_text()
        self._update_artists()

    def _update_artists(self):
        if self.useblit:
            if self._background is not None:
                self.canvas.restore_region(self._background)
            else:
                self._background = self.canvas.copy_from_bbox(self.fig.bbox)

            for artist in self._artists:
                self.ax.draw_artist(artist)

            self.canvas.blit(self.fig.bbox)
        else:
            self.canvas.draw_idle()

    def _update_text(self):
        detail_string = "; ".join(
            (
                f"L: {self.length_fmt.format(self.ruler_length)}",
                f"dx: {self.length_fmt.format(self.ruler_dx)}",
                f"dy: {self.length_fmt.format(self.ruler_dy)}",
                f"ang: {self.angle_fmt.format(self.ruler_angle)}",
            )
        )

        self._axes_text.set_text(detail_string)
        if self._print_text:
            print(detail_string)

    def _get_cursor(self, event):
        if not self.active:
            return Cursors.POINTER
        if any(self._over_marker(event)) or self._mouse1_pressed and self._ruler_moving:
            if self._shift_pressed:
                return Cursors.RESIZE_HORIZONTAL
            if self._control_pressed:
                return Cursors.RESIZE_VERTICAL
            return Cursors.MOVE
        return Cursors.SELECT_REGION

    def _update_cursor(self, event):
        self.fig.canvas.set_cursor(self._get_cursor(event))

    def _on_release(self, event):
        self._mouse_buttons.add(event.button)
        self._ruler_drawing = False
        self._ruler_moving = False
        self._end_a_lock = False
        self._end_b_lock = False
        self._end_c_lock = False

    @property
    def ruler_length(self):
        pos0, pos1 = self._ruler.get_path().vertices
        return np.hypot((pos1[0] - pos0[0]), (pos0[1] - pos1[1]))

    @property
    def ruler_dx(self):
        pos0, pos1 = self._ruler.get_path().vertices
        return pos1[0] - pos0[0]

    @property
    def ruler_dy(self):
        pos0, pos1 = self._ruler.get_path().vertices
        return pos1[1] - pos0[1]

    @property
    def ruler_angle(self):
        pos0, pos1 = self._ruler.get_path().vertices
        angle = np.arctan2(pos1[0] - pos0[0], pos1[1] - pos0[1])

        if self.angle_in_degrees:
            return angle * 180 / np.pi
        else:
            return angle
