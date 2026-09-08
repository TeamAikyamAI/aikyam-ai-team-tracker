"""The Aikyam mark, rebuilt as real vector geometry from the brand screenshot.

Circle centres/radii were fitted to the artwork's outline by least squares, and
each gradient's axis, endpoints and stop colours were fitted to the actual pixel
colours along that gradient's own axis. Rendered against the original at source
size this scores a mean per-channel difference of 1.6%, with the residual
confined to anti-aliased edges and the source image's own sensor-style noise.

This ships as the seeded default so a fresh install is never blank, and is also
the fallback served if an admin removes the uploaded logo.
"""

DEFAULT_LOGO_FILENAME = "aikyam-logo.svg"
DEFAULT_LOGO_CONTENT_TYPE = "image/svg+xml"

DEFAULT_LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 147.8 153.9" role="img"'
    ' aria-label="Aikyam AI Team Tracker">'
    '<defs>'
    '<linearGradient id="gA" gradientUnits="userSpaceOnUse"'
    ' x1="-8.812" y1="8.218" x2="-66.698" y2="81.707">'
    '<stop offset="0" stop-color="#7936C1"/><stop offset="1" stop-color="#133350"/>'
    '</linearGradient>'
    '<linearGradient id="gB" gradientUnits="userSpaceOnUse"'
    ' x1="45.804" y1="-53.383" x2="12.276" y2="-16.229">'
    '<stop offset="0" stop-color="#2E447D"/><stop offset="1" stop-color="#579FCC"/>'
    '</linearGradient>'
    '<linearGradient id="gL" gradientUnits="userSpaceOnUse"'
    ' x1="70.402" y1="59.987" x2="102.327" y2="86.505">'
    '<stop offset="0" stop-color="#17435C"/><stop offset="1" stop-color="#F1888D"/>'
    '</linearGradient>'
    '</defs>'
    '<circle cx="61.769" cy="92.131" r="61.769" fill="url(#gA)"/>'
    '<circle cx="106.113" cy="41.688" r="41.688" fill="url(#gB)"/>'
    '<path d="M 65.953 30.505 A 61.769 61.769 0 0 1 122.351 80.084'
    ' A 41.688 41.688 0 0 1 65.953 30.505 Z" fill="url(#gL)"/>'
    '</svg>'
).encode("utf-8")
