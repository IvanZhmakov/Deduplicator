from PIL import Image, ImageTk

def load_image(path, label, size=(256, 256)):
    img = Image.open(path).resize(size, Image.NEAREST)
    photo = ImageTk.PhotoImage(img)
    label.config(image=photo)
    label.image = photo
