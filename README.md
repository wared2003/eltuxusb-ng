# eltuxusb

This program aims to provide Linux support for the data loggers from Lascar Electronics.

## Supported hardware

This program only works with the following devices:

 * ELUSB-1
 * ELUSB-2
 * ELUSB-2-LCD

Support will be extended to other Lascar products if possible (if we actually have another product in our hands).

## Requirements

 * Python 3.9+
 * GTK4 and libadwaita (with their GObject introspection bindings)
 * PyUSB (with libusb)
 * matplotlib

On Debian 13 (Trixie) / Ubuntu:

    sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 python3-usb python3-matplotlib

## Installation

### From source (PIP)

    pip install .

The `eltuxusb` command is then available in your $PATH.

### Flatpak

Install it from the signed Flatpak repository published on GitHub Pages:

    wget https://wared2003.github.io/eltuxusb-ng/eltuxusb-repo.gpg
    flatpak remote-add --if-not-exists --gpg-import=eltuxusb-repo.gpg eltuxusb https://wared2003.github.io/eltuxusb-ng
    flatpak install eltuxusb com.github.eltuxusb.eltuxusb

Or install the single-file bundle attached to each GitHub release (tags `v*`):

    wget https://github.com/wared2003/eltuxusb-ng/releases/latest/download/com.github.eltuxusb.eltuxusb.flatpak
    flatpak install com.github.eltuxusb.eltuxusb.flatpak

Or build it yourself from the manifest in `flatpak/`:

    flatpak-builder --user --install --force-clean build-dir flatpak/com.github.eltuxusb.eltuxusb.json

The udev rule described below is still required on the host for USB access.

## USB permissions

We need read and write access to the device (libusb opens it read-write even for
read-only operations). As a non-root user, install the udev rule shipped in this
repository and reload the rules:

    sudo cp 10-local.rules /etc/udev/rules.d/10-local.rules
    sudo udevadm control --reload-rules
    sudo udevadm trigger --action=change --subsystem-match=usb --attr-match=idVendor=10c4

The rule (`10-local.rules`) is:

    SUBSYSTEM=="usb",ATTR{idVendor}=="10c4",ATTR{idProduct}=="0002",MODE="0666",GROUP="usbusers"

Unplug and replug the logger so the rule applies, then check that the device is
visible and that its node is writable by your user:

    lsusb -d 10c4:0002
    ls -l /dev/bus/usb/<bus>/<device>     # expect crw-rw-rw- (MODE 0666)

If you get `Access denied (Errno 13)` when running eltuxusb, the rule is missing
or the device was plugged before the rules were reloaded.

## Usage

Run the program:

    eltuxusb

It can also be used from the command line without the graphical interface:

    eltuxusb -D /home/user/out.txt     # download the recordings to a file
    eltuxusb -R /home/user/config.txt  # !WARNING! reprogram the device configuration from a file !WARNING!
    eltuxusb -d                        # debug mode (nothing is written to the device)

## Remove

To remove the program:

    sudo pip uninstall eltuxusb
