# matplotlib-ruler

An interactive ruler tool to measure distances and angles in matplotlib.

Based on [`terranjp/matplotlib-tools`](https://github.com/terranjp/matplotlib-tools) which was heavily inspired by the tool in ImageJ.

## Installation

Install using pip: `pip install matplotlib_ruler`

### Requirements

`matplotlib_ruler` has two dependecies: `numpy` and `matplotlib`.

## Usage

1. Hold left click drag and release to draw the ruler in the axes.
  - Hold shift while dragging to lock the ruler to the horizontal axis.
  - Hold control while drawing to lock the ruler to the vertical axis.

2. Right click one of the markers to move the ruler.

The keyboard can be used to activate and deactivate the ruler and toggle
visibility of the line and text:

'm' : Toggles the ruler on and off.

'ctl+m' : Toggles the visibility of the ruler and text.

## Example

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


![Ruler Gif](/docs/ruler_example.gif?raw=True)

## License

The original [`terranjp/matplotlib-tools`](https://github.com/terranjp/matplotlib-tools) code was released without a specified license, all rights are reserved by the original author.

Modifications are released under the MIT license, see the [`LICENSE`](/LICENSE) file for details.
