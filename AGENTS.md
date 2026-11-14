# AGENTS.md — eltuxusb-ng (branche vibe/python3-gtk4-migration)

Notes et acquis de la migration Python 3 + GTK4/libadwaita (session du 2026-11-13).
Référence comportementale : repo `eltuxusb/eltuxusb`, branche master (Python 2).

## Environnement (Debian 13 / GNOME)

- Paquets : `sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 python3-usb python3-matplotlib`
- Pas de venv (libs GTK système). Si besoin : `python3 -m venv --system-site-packages`.
- Lancement : `python3 -m eltuxusb` (UI), `-d` (debug, n'écrit JAMAIS sur le device), `-v` (affiche `eltuxusb version 0.6`), `-D <fichier>` (CLI download), `-R <fichier>` (recover, DESTRUCTIF).
- Règle udev requise pour tout accès device (même lecture seule : libusb ouvre en O_RDWR) :
  `10-local.rules` à la racine du repo → `/etc/udev/rules.d/10-local.rules`
  (`SUBSYSTEM=="usb",ATTR{idVendor}=="10c4",ATTR{idProduct}=="0002",MODE="0666",GROUP="usbusers"`),
  puis `udevadm control --reload-rules` + `udevadm trigger --action=change --subsystem-match=usb --attr-match=idVendor=10c4`.
- Sans mot de passe sudo dans un sandbox : lancer l'install via `pkexec` en arrière-plan →
  boîte polkit sur l'écran GNOME de l'utilisateur (DISPLAY=:1), approbation manuelle.
- Display X11 dispo (`:1`). Captures d'écran : `import -window root out.png` (ImageMagick),
  liste des fenêtres : `xwininfo -root -children`.

## Règles de sécurité (non négociables)

- Aucun test d'écriture (Apply, `-R`) sur un device avec données importantes sans accord explicite.
- Toujours valider en `-d` avant un test d'écriture réel ; device sacrificial uniquement.
- `-R` (recover) est destructif : interdit sauf instruction explicite.
- Ne pas modifier le protocole USB dans `el_device.py` (séquences de commandes, tailles de buffer)
  sans preuve que c'est la cause — partie validée par le matériel. Les `release_interface` sont
  de la gestion de ressources, pas du protocole.
- Ne pas merger la PR, ne pas toucher à `main`, ne pas rebaser la branche de migration.

## Pièges GTK4 / libadwaita rencontrés

- `Gtk.DropDown(strings=...)` → `TypeError` (pas une propriété constructible) : utiliser
  `Gtk.DropDown.new_from_strings(list)`.
- Ne jamais appender deux fois le même widget à un parent → `Gtk-CRITICAL gtk_box_append`.
- `Gtk.FileDialog` : `dialog.save(parent, None, cb)` / `dialog.open(...)`, finir avec
  `save_finish(result)` / `open_finish(result)` (lever `GLib.Error` si annulé).
- Graphe embarqué : `from matplotlib.backends.backend_gtk4agg import FigureCanvas`,
  `Adw.Window` + `set_content(canvas)`.
- I/O USB dans un thread (worker) puis `GLib.idle_add` pour toucher l'UI.

## Pièges pyusb 1.x (cause de vrais bugs)

- Les transferts bulk auto-claim l'interface 0 ; chaque `usb.core.find()` ouvre un NOUVEAU handle.
  Si une op ne release pas l'interface, le prochain `init()` échoue :
  `usb.core.USBError: [Errno 16] Resource busy` au `claim_interface`.
  → `usb.util.release_interface(self.address, 0x00)` à la fin de chaque op
  (déjà fait dans `config_read`, ajouté dans `config_write` et `recordings_read`).
- Sans règle udev : `USBError: [Errno 13] Access denied` au premier `ctrl_transfer` →
  à catcher dans l'UI (`refresh`, worker download) et le CLI (`el_cmd.download`).
- `el1_device.init()` et `clear_flag_bits()` renvoient `None` en cas de SUCCÈS, `False` en échec :
  ne PAS tester la truthiness (`a and b and c` échoue toujours) → utiliser `is not False` / `== False`.

## Protocole / device (EL-USB-1/2/2-LCD, vendor 10c4:0002)

- Buffer config : 64 octets (EL-USB-1) / 128 (EL-USB-2/2-LCD). Octet 0 = modèle
  (1=elusb1_16, 2=elusb1_17, 3=elusb2, 12=elusb2lcd). Nom en [2:18], start time [18:24],
  offset [24:28] (little-endian), sample rate [28:30], sample count [30:32], flag bits [32:34]
  (chaîne de 16 bits inversée par octet : bit 8 = logging/delayed, bit 9 = NOT downloaded),
  HAL/LAL [34],[35], unit [46] (0=°C), SN [52:56], hum alarms [56],[57].
- Le device marque lui-même les données « downloaded » après une lecture (bit 9 passe à 0).
- Après un Apply, il faut débrancher/rebrancher pour démarrer depuis l'état stopped
  (message « Ready, please remove device »). Rebranchement simulable en root :
  `echo 0 > /sys/bus/usb/devices/<dev>/authorized; sleep 2; echo 1 > .../authorized`
  (trouver le chemin via `idVendor` == 10c4). Le firmware recalcule l'offset de démarrage
  au power-on — comportement normal, pas un bug.
- Le parsing CSV s'arrête au premier octet 255 (fin des données).

## Format CSV (ELWINUSB)

`nom,Time,Celsius(°C)[,High Alarm,Low Alarm][,Humidity(%rh),...],dew point(°C),Serial Number`
— n° de série uniquement sur la ligne 1 ; dates `dd/mm/yyyy HH:MM:SS` ; 2478 enregistrements
réels téléchargés avec succès sur un EL-USB-2-LCD (série 061204174, nom « 2 EP FRIGO SDR »).

## Tests : méthode qui a marché

- `python3 -m py_compile eltuxusb/*.py` avant chaque commit.
- Simuler « pas de device » : patcher `usb.core.find = lambda **kw: None` dans un harness
  (les harness de test étaient dans `/tmp/scratch/`, ex. `harness_nodev.py`, `harness_device.py`).
- Données synthétiques : bloc commenté dans `el_parse.py` du repo py2
  (clone de référence : `git clone https://github.com/eltuxusb/eltuxusb`).
- Tester dans l'ordre : sans device → device (-d) → écritures réelles (si autorisé).
- Ordre des tests UI : Refresh → Download → Graph → New recording/Apply (-d d'abord) → Stop → CLI -D.

## Flatpak + pipeline GitHub Pages (option retenue, pas Flathub)

- Manifeste : `flatpak/com.github.eltuxusb.eltuxusb.json` — runtime `org.gnome.Platform//51`
  (48 est EOL depuis 2026-03), module `libusb` 1.0.29 compilé `--disable-udev`
  (pyusb sinon : `NoBackendError: No backend available`), puis pip pyusb/matplotlib/app.
  `build-options.build-args: ["--share=network"]` est INDISPENSABLE : le bac à sable
  flatpak-builder n'a pas le réseau par défaut → pip échoue (DNS) sinon.
  `--device=all` dans finish-args pour l'USB ; la règle udev hôte reste nécessaire.
- Dépôt publié sur GitHub Pages : workflow `.github/workflows/flatpak.yml`
  (déclenché sur tags `v*` + workflow_dispatch) build avec `flatpak-builder --repo=repo`
  puis déploie `repo/` via `actions/configure-pages@v5` + `upload-pages-artifact@v3` + `deploy-pages@v4`.
  Prérequis manuel UNE FOIS : Settings → Pages → Source = « GitHub Actions ».
- Le dépôt est SIGNÉ GPG : la workflow importe la clé privée depuis le secret GitHub
  `FLATPAK_GPG_PRIVATE_KEY` (clé ed25519, sans passphrase, fingerprint
  `73015E7FEDCE7BFD91624423CE1D8D02552368D2`) et build avec `--gpg-sign=<fpr>` ;
  la clé publique `flatpak/eltuxusb-repo.gpg` est copiée dans `repo/` donc servie sur Pages.
  Clé privée sur la machine du proprio : `~/eltuxusb-repo-signing-private.asc` (à coller
  dans Settings → Secrets → Actions → `FLATPAK_GPG_PRIVATE_KEY`, ne PAS committer).
- Install utilisateur (dépôt signé) :
  `wget https://wared2003.github.io/eltuxusb-ng/eltuxusb-repo.gpg` puis
  `flatpak remote-add --if-not-exists --gpg-import=eltuxusb-repo.gpg eltuxusb https://wared2003.github.io/eltuxusb-ng`
  puis `flatpak install eltuxusb com.github.eltuxusb.eltuxusb`.
  Sans la clé, l'install échoue : « Can't pull from untrusted non-gpg verified remote ».
- Test local du build : `flatpak-builder --user --force-clean --state-dir=<dir même fs que build> --repo=<repo> <build> flatpak/...json`
  (state dir par défaut dans le repo = autre filesystem que /tmp → flatpak-builder 1.4.4 sort en erreur 1).
- Piège : `application_id="com.github.eltuxusb.eltuxusb"` → une instance flatpak se « handoff »
  à une instance système déjà lancée et sort 0 immédiatement (comportement normal, pas un bug).

## Push depuis un sandbox sans identifiants git

`git push` HTTPS échoue (pas de credentials). Utiliser le connecteur GitHub :
`tools.connector_github_app.push_files({owner:"wared2003", repo:"eltuxusb-ng",
branch:"vibe/python3-gtk4-migration", message, files:[{path, content}]})` — un commit par fix.
La branche distante peut contenir des commits absents localement (ex. fix README 6dbe24c) :
faire `git fetch` puis `git merge origin/vibe/python3-gtk4-migration` (PAS de rebase).
Vérifier ensuite : `git fetch origin` + diff des fichiers branche distante vs local.
