from os import listdir
from os.path import join
from PIL import Image

def crop(im, width, height):
    im_width, im_height = im.size
    for i in range(im_height // height):
        for j in range(im_width // width):
            box = (j * width, i * height, (j + 1) * width, (i + 1) * height)
            yield im.crop(box)

def split():
    width = 4576
    path = "C:\\Users\\brent\\PycharmProjects\\AgentGlitch\\Assets\\Misc\\__START___bg"
    im = Image.open(path + ".png")
    _, im_height = im.size
    for i, pasteable in enumerate(crop(im, width, im_height), 0):
        new_im = Image.new("RGBA", (width, im_height), 255)
        new_im.paste(pasteable)
        print(path + "_" + str(i) + ".png")
        new_im.save(path + "_" + str(i) + ".png")

def merge(files):
    print("Starting...")
    im_list = []
    for file in files:
        im_list.append(Image.open(file))
    im_width, im_height = im_list[0].size
    data = []
    for y in range(im_height):
        for im in im_list:
            for x in range(im_width):
                data.append(im.getpixel((x, y)))
    new = Image.new(im_list[0].mode, (im_width * len(im_list), im_height))
    new.putdata(data)
    print("Finished.")
    return new

## could add random buildings, with random height, random width (both > some threshold), and only draw the pixels on the red area - maybe even draw windows too if possible
def recolour(im):
    print("Starting...")
    marker = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 255, 255)]
    data = []
    width, height = im.size
    colours = [[0, (0, 0, 0, 255)], [1152, (60, 56, 101, 255)], [2208, (219, 129, 68, 255)], [3647, (60, 56, 101, 255)], [3648, (121, 197, 142, 255)], [3650, (121, 197, 142, 255)], [3651, (115, 166, 129, 255)], [3652, (115, 166, 129, 255)], [3653, (121, 197, 142, 255)], [3655, (121, 197, 142, 255)], [3656, (215, 219, 224, 255)], [height, (0, 0, 0, 255)]] #(81, 206, 174, 255)
    i = 0
    for y in range(height):
        if i < len(colours) - 1 and y >= colours[i + 1][0]:
            i += 1
        for x in range(width):
            pixel = im.getpixel((x, y))
            if pixel in [marker[0], marker[1]]:
                multiplier = (y - colours[i][0]) / (colours[i + 1][0] - colours[i][0])
                r = int((colours[i][1][0] * (1 - multiplier)) + colours[i + 1][1][0] * multiplier)
                g = int((colours[i][1][1] * (1 - multiplier)) + colours[i + 1][1][1] * multiplier)
                b = int((colours[i][1][2] * (1 - multiplier)) + colours[i + 1][1][2] * multiplier)
                a = int((colours[i][1][3] * (1 - multiplier)) + colours[i + 1][1][3] * multiplier)
                pixel = (r, g, b, a)
            elif pixel in [marker[2], marker[3]]:
                pixel = (88, 88, 88, 255)
            data.append(pixel)
    new = Image.new(im.mode, im.size)
    new.putdata(data)
    print("Finished.")
    return new

#for i in range(6):
#    recolour(Image.open("C:\\Users\\brent\\PycharmProjects\\AgentGlitch\\Assets\\Misc\\__START___bg_" + str(i) + ".png")).save("C:\\Users\\brent\\PycharmProjects\\AgentGlitch\\Assets\\Misc\\__START___bg_" + str(i) + "_rc.png")

#path = "C:\\Users\\brent\\PycharmProjects\\AgentGlitch\\Assets\\Misc\\"
#files = [path + "__START___bg_0_rc.png", path + "__START___bg_1_rc.png", path + "__START___bg_2_rc.png", path + "__START___bg_3_rc.png", path + "__START___bg_4_rc.png", path + "__START___bg_5_rc.png"]
#merge(files).save(path + "__START___bg_rc.png")

def convert(im, base, target, lips=True):
    colours = {"skin": {"white": (242, 188, 126, 255), "black": (59, 21, 21, 255), "asian": (250, 220, 162, 255), "brown": (168, 133, 92, 255)},
                "shadow": {"white": (202, 168, 130, 255), "black": (103, 58, 58, 255), "asian": (212, 179, 114, 255), "brown": (108, 76, 39, 255)},
                "highlight": {"white": (251, 223, 177, 255), "black": (165, 121, 121, 255), "asian": (245, 229, 197, 255), "brown": (203, 164, 120, 255)},
                "hair": {"white": (185, 122, 86, 255), "black": (33, 28, 37, 255), "asian": (33, 28, 37, 255), "brown": (71, 42, 41, 255)},
                "lips": {"white": (206, 110, 135, 255), "black": (199, 48, 48, 255), "asian": (199, 48, 48, 255), "brown": (199, 48, 48, 255)}}

    conversion = [[colours["skin"][base], colours["skin"][target]], [colours["shadow"][base], colours["shadow"][target]], [colours["highlight"][base], colours["highlight"][target]], [colours["hair"][base], colours["hair"][target]]]
    if lips:
        conversion += [[colours["lips"][base], colours["lips"][target]]]

    #conversion = [[(255, 182, 24, 255), colours["skin"]["white"]], [(255, 202, 24, 255), colours["skin"]["white"]], [(63, 72, 204, 255), (204, 176, 160, 255)], [(251, 107, 45, 255), (255, 255, 255, 255)], [(84, 85, 85, 255), (29, 29, 29, 255)], [(145, 128, 128, 255), colours["shadow"]["white"]]]
    #conversion = [[(242, 189, 128, 255), colours["skin"][target]], [(242, 189, 129, 255), colours["skin"][target]], [(186, 123, 88, 255), colours["hair"][target]]]
    data = []
    for pixel in im.getdata():
        replaced = False
        for color in conversion:
            if pixel == color[0]:
                data.append(color[1])
                replaced = True
                break
        if not replaced:
            data.append(pixel)

    new = Image.new(im.mode, im.size)
    new.putdata(data)
    return new

def run_conversion():
    sub = "RetroPlayer7"
    path = "C:\\Users\\brent\\PycharmProjects\\AgentGlitch\\Assets\\Sprites\\" + sub
    for file in listdir(path):
        filepath = join(path, file)
        print(filepath)
        convert(Image.open(filepath), "white", "brown", lips=True).save(filepath)

run_conversion()