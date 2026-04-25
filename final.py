def create_slide(title, points):
    img = Image.new("RGB", (1280, 720), "#ffffff")
    draw = ImageDraw.Draw(img)

    title_font = ImageFont.truetype("Roboto-Bold.ttf", 120)
    point_font = ImageFont.truetype("Roboto-Bold.ttf", 75)

    # Title
    draw.text((80, 80), title.upper(), fill="black", font=title_font)

    # Line
    draw.line((80, 230, 1200, 230), fill="black", width=4)

    # Points
    y = 320
    for p in points:
        draw.text((120, y), f"• {p}", fill="black", font=point_font)
        y += 140

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    img.save(path)
    return path
