from PIL import Image, ImageFilter, ImageEnhance
img = Image.open('app/photos/scrip.png').convert('RGBA')
# Улучшение: шарпинг + контраст
enhancer = ImageEnhance.Sharpness(img)
img = enhancer.enhance(2.0)  # Увеличить резкость
enhancer = ImageEnhance.Contrast(img)
img = enhancer.enhance(1.2)
img.save('output.png', 'PNG')  # Альфа сохраняется
