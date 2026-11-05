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

## Instalar en la Raspberry Pi (Plasma Mobile) o en cualquier Linux

Sin Flatpak y sin root (solo `apt` para las dependencias). En la terminal de la Pi, o por SSH:

```bash
sudo apt update && sudo apt install -y git python3-pygame
git clone https://github.com/Philip-Mccoll-aux/tux-flap
cd tux-flap && ./install.sh
```

Queda en el menú de aplicaciones como **Tux Flap** (categoría Juegos) y se lanza también con `~/.local/bin/tuxflap`.

- **Actualizar:** `cd tux-flap && git pull && ./install.sh`
- **Desinstalar:** `./install.sh --uninstall` (tu récord se conserva en `~/.local/share/tuxflap/score.json`)
- Si no aparece en el menú, espera unos segundos o cierra y abre la sesión.
- Si el toque o el tamaño de la pantalla fallan, prueba con el driver de video a mano:
  `SDL_VIDEODRIVER=wayland tuxflap` (nativo) o `SDL_VIDEODRIVER=x11 tuxflap` (XWayland).

## Construir el Flatpak

```bash
flatpak install flathub org.freedesktop.Platform//25.08 org.freedesktop.Sdk//25.08
flatpak-builder --user --install --force-clean build flatpak/io.github.philip_mccoll_aux.TuxFlap.yml
flatpak run io.github.philip_mccoll_aux.TuxFlap
```

El manifiesto incluye ruedas de pygame-ce para **x86_64 y aarch64** (la Raspberry Pi 4).
Es un manifiesto **de desarrollo** para probar el Flatpak en local: usa ruedas precompiladas, por lo que no sirve tal cual para Flathub (ver abajo).

## Discover y Flathub

Discover muestra el catálogo de **Flathub** y las fuentes Flatpak que añada el usuario. Para entrar en Flathub hay que cumplir sus
[requisitos](https://docs.flathub.org/docs/for-app-authors/requirements), entre ellos:

- compilar todo desde el código fuente (el manifiesto de este repo usa ruedas precompiladas de pygame-ce);
- un historial de desarrollo y mantenimiento sostenido;
- su [política de IA generativa](https://docs.flathub.org/docs/for-app-authors/requirements#generative-ai-policy):
  declarar el material generado con IA, y escribir a mano el manifiesto y el pull request.

Mientras tanto, la forma de instalarlo es `./install.sh` (arriba).

## Licencia

GPL-3.0-or-later. "Tux" es la mascota de Linux (Larry Ewing); aquí se redibuja por código.
