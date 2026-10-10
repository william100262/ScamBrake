# OCR photo regression fixtures

These unchanged images are bundled so real-engine tests run without network
access or a scikit-image dependency. They represent photographs with no readable
payment message, rather than asserting there are no letters anywhere in a photo.

- `coffee.png`: Rachel Michetti, courtesy of Pikolo Espresso Bar, CC0.
  [Source file (scikit-image v0.19.3)](https://github.com/scikit-image/scikit-image/blob/v0.19.3/skimage/data/coffee.png).
- `astronaut.png`: NASA photograph of Eileen Collins, public domain.
  [Source file (scikit-image v0.19.3)](https://github.com/scikit-image/scikit-image/blob/v0.19.3/skimage/data/astronaut.png).

[Image descriptions and licensing](https://scikit-image.org/docs/0.25.x/api/skimage.data.html).
Downloaded October 10, 2026. The coffee photograph produces enough raw OCR noise
on the tested Tesseract 5.4 engine to pass the old three-character acceptance rule;
the new confidence filter rejects it. Recognition can vary by engine/model version.
