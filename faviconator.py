from PIL import Image

filename = r"src/assets/images/rect218-7.png"
img = Image.open(filename)
img.save("src/assets/images/favicon.ico")
