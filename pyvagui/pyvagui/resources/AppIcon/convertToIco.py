from PIL import Image
Image.open("C:\\src\\Abschlussprojekt\\Code\\Own\\pyvagui\\pyvagui\\resources\\AppIcon\\AppIcon.png").save(
    "C:\\src\\Abschlussprojekt\\Code\\Own\\pyvagui\\pyvagui\\resources\\AppIcon\\AppIcon.ico",
    sizes=[(16, 16), (32, 32), (48, 48), (256, 256)],
)