# Tux Flap 🐧

Juego tipo Flappy Bird: Tux aletea entre **témpanos cilíndricos** de hielo. Pensado para
pantallas táctiles verticales (Plasma Mobile en Raspberry Pi 4, ver
[Little Rascal Smart Phone](https://github.com/Philip-McColl-sd/Little_Rascal_Smart_Phone)),
pero también se juega en escritorio.

- **Tocar / clic / Espacio / ↑** → aletear · **F11** → pantalla completa · **Esc** → salir
- Récord guardado en `~/.local/share/tuxflap/score.json` (en Flatpak, dentro de `~/.var/app/<id>/`)
- **El mundo muta sin parar y de forma continua** (no hay «niveles» con saltos): un progreso `u` crece con
  cada punto, incluso entre columna y columna, y no tiene techo. Hitos: Edén de Hielo (0) → El Deshielo →
  Plaga de Fuego → Langostas y Relámpagos → Apocalipsis (u = 4, ~38 puntos) → ... y sigue.
  - **Entorno generativo:** la paleta fluye sin escalones, se abren ojos en el cielo y en las columnas
    que siguen a Tux, aparecen nubes de sangre, langostas, relámpagos, meteoros y un eclipse.
  - **Tux se vuelve un serafín bíblico, acumulativo:** aura dorada, aureola, alas de plumas que pasan de
    negro a blanco y se multiplican (hasta seis pares) con ojos sobre las plumas, ojos que se abren por el cuerpo y
    ruedas con ojos (ofanim) girando alrededor. Solo el cuerpo cuenta para las colisiones.
  - Además sube la velocidad, el hueco se estrecha y las columnas se mueven (con límites razonables).
- Tux está animado: aleteo en 6 posiciones, squash & stretch, parpadeo, pies que cuelgan al caer,
  cara de susto en picada, plumas y polvo, y una muerte con vueltas, rebote y estrellitas.
- Todos los gráficos se dibujan por código: sin imágenes de terceros
- Se inicia a pantalla completa automáticamente en pantallas ≤ 900 px (móviles)

## Probar sin instalar

```bash
pip install pygame-ce
python3 -m tuxflap          # opciones: --fullscreen | --windowed
```

En Debian/Raspberry Pi OS: `sudo apt install python3-pygame` también sirve.

## Construir el Flatpak

```bash
flatpak install flathub org.freedesktop.Platform//25.08 org.freedesktop.Sdk//25.08
flatpak-builder --user --install --force-clean build flatpak/io.github.philip_mccoll_aux.TuxFlap.yml
flatpak run io.github.philip_mccoll_aux.TuxFlap
```

El manifiesto incluye ruedas de pygame-ce para **x86_64 y aarch64** (la Raspberry Pi 4).

## Publicarlo para que aparezca en Discover

Discover (con `plasma-discover-backend-flatpak`) lee el catálogo de **Flathub**. Pasos:

1. Sube este proyecto al repositorio `Philip-Mccoll-aux/tux-flap` (las URLs de `data/*.metainfo.xml` ya apuntan ahí).
2. **ID de la app**: `io.github.philip_mccoll_aux.TuxFlap`, que corresponde a la cuenta de GitHub que envía el PR a Flathub.
   Si algún día lo cambias, renombra los 3 archivos de `data/`, el manifiesto y `APP_ID` en `tuxflap/game.py`.
3. Valida: `appstreamcli validate --pedantic data/*.metainfo.xml` y `desktop-file-validate data/*.desktop`.
4. Abre un PR en <https://github.com/flathub/flathub> (rama `new-pr`) siguiendo
   <https://docs.flathub.org/docs/for-app-authors/submission>. Tras la aprobación, aparecerá en Discover.

Mientras tanto se puede instalar localmente con el paso de construcción de arriba;
Discover la mostrará en «Instaladas».

## Licencia

GPL-3.0-or-later. "Tux" es la mascota de Linux (Larry Ewing); aquí se redibuja por código.
