# favicon-generator

Modern websites use a variety of different image sizes and formats to be useable on different devices and browsers. I wanted a script that would take my input SVG and generate all of the needed icons, plus a manifest to make my website a [Progressive Web Application (PWA)][PWA]. So, I turned to ChatGPT, which generated this script after some back-and-forth.

```text
usage: favicon-generator.py [-h] [--icons-dir ICONS_DIR] [--manifest-dir MANIFEST_DIR] [--pwa-theme PWA_THEME] [--pwa-bg PWA_BG]
                            [--pwa-name PWA_NAME] [--pwa-short-name PWA_SHORT_NAME] [--maskable-padding MASKABLE_PADDING]
                            [--pinned-svg PINNED_SVG] [--safari-pinned-color SAFARI_PINNED_COLOR] [--make-browserconfig] [--no-ico]
                            [--no-apple-touch] [--no-maskable] [--no-manifest] [--favicon-sizes FAVICON_SIZES] [--flask]
                            [--public-prefix PUBLIC_PREFIX]
                            source

Generate favicon and PWA icons.

positional arguments:
  source                Source SVG or PNG.

options:
  -h, --help            show this help message and exit
  --icons-dir ICONS_DIR
  --manifest-dir MANIFEST_DIR
  --pwa-theme PWA_THEME
                        Theme color for PWA meta.
  --pwa-bg PWA_BG       Background color for PWA meta.
  --pwa-name PWA_NAME   Full PWA name.
  --pwa-short-name PWA_SHORT_NAME
                        Short PWA name.
  --maskable-padding MASKABLE_PADDING
  --pinned-svg PINNED_SVG
  --safari-pinned-color SAFARI_PINNED_COLOR
                        Color used for <link rel='mask-icon' ... color=...>. Only applied if --pinned-svg is provided.
  --make-browserconfig
  --no-ico              Skip generating favicon.ico.
  --no-apple-touch      Skip apple-touch-icon.png.
  --no-maskable         Skip maskable icon and manifest entry.
  --no-manifest         Skip writing site.webmanifest and omit its <link>.
  --favicon-sizes FAVICON_SIZES
                        Comma-separated PNG favicon sizes to generate (e.g., 16,32,48,96,128,256).
  --flask               Output Flask/Jinja paths.
  --public-prefix PUBLIC_PREFIX
                        Base URL prefix for HTML snippet (ignored with --flask). Example: /assets/
```

[PWA]: https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps
