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

Download the single-file bundle from the latest GitHub release and install it:

    wget https://github.com/wared2003/eltuxusb-ng/releases/latest/download/com.github.eltuxusb.eltuxusb.flatpak
    flatpak install com.github.eltuxusb.eltuxusb.flatpak

(The bundle is rebuilt on every push to `main` — downloadable from the workflow run
artifacts — and attached to the GitHub release automatically on every `v*` tag.)

Or build it yourself from the manifest in `flatpak/`:

    flatpak-builder --user --install --force-clean build-dir flatpak/com.github.eltuxusb.eltuxusb.json

The udev rule described below is still required on the host for USB access.

## USB permissions

One command installs a udev rule giving your user read/write access to the logger
(libusb opens the device read-write even for read-only operations):

    echo 'SUBSYSTEM=="usb",ATTR{idVendor}=="10c4",ATTR{idProduct}=="0002",MODE="0666"' | sudo tee /etc/udev/rules.d/10-local.rules
    sudo udevadm control --reload-rules
    sudo udevadm trigger --action=change --subsystem-match=usb --attr-match=idVendor=10c4

Unplug and replug the logger so the rule applies, then check that its device node
is world-writable:

    DEV=$(lsusb -d 10c4:0002 | awk '{print "/dev/bus/usb/" $2 "/" $4}' | tr -d ':')
    ls -l "$DEV"        # expect crw-rw-rw-

Quick fix without any rule (lost on replug): `sudo chmod 666 "$DEV"`

If eltuxusb reports `Access denied (Errno 13)`, the rule is missing or the device
was plugged before the rules were reloaded.

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
