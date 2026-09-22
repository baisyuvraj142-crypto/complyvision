"""
ComplyVision - Sample Label Image Generator
Generates realistic packaged commodity label test photos for live hackathon demonstration.
Covers:
1. Clean Compliant Pass
2. Missing Mfg Date Violation (Fail)
3. Undersized MRP Font Violation (Fail - Font Ratio Check)
4. Missing Consumer Care Violation (Fail)
5. Blurry Image (NFR-3 Re-capture Warning)
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def get_font(size: int, bold: bool = False):
    try:
        # Common Windows standard fonts
        font_name = "arialbd.ttf" if bold else "arial.ttf"
        return ImageFont.truetype(font_name, size)
    except Exception:
        return ImageFont.load_default()

def create_sample_label(
    filename: str,
    brand_title: str,
    product_subtitle: str,
    mrp_text: str,
    mrp_font_size: int,
    qty_text: str,
    mfg_text: str,
    mfr_text: str,
    care_text: str,
    bg_color=(248, 249, 250),
    accent_color=(30, 41, 59),
    blur: bool = False
):
    width, height = 750, 520
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Decorative header banner
    draw.rectangle([(0, 0), (width, 85)], fill=(37, 99, 235))
    draw.text((25, 15), brand_title, fill=(255, 255, 255), font=get_font(28, bold=True))
    draw.text((25, 52), product_subtitle, fill=(219, 234, 254), font=get_font(16))

    # Outer border
    draw.rectangle([(8, 8), (width - 8, height - 8)], outline=(203, 213, 225), width=3)

    # Product visual box placeholder
    draw.rectangle([(480, 110), (715, 300)], fill=(241, 245, 249), outline=(148, 163, 184), width=2)
    draw.text((515, 195), "[ PACKAGED GOOD ]", fill=(100, 116, 139), font=get_font(16, bold=True))
    draw.text((545, 225), "FSSAI LIC NO.", fill=(148, 163, 184), font=get_font(12))
    draw.text((520, 242), "10018022008123", fill=(71, 85, 105), font=get_font(14, bold=True))

    # Mandatory Declarations Panel
    curr_y = 110
    draw.text((25, curr_y), "STATUTORY DECLARATIONS (LEGAL METROLOGY):", fill=(71, 85, 105), font=get_font(13, bold=True))
    curr_y += 30

    # Net Quantity (standard baseline font size: 22)
    if qty_text:
        draw.text((25, curr_y), f"Net Quantity: {qty_text}", fill=(15, 23, 42), font=get_font(22, bold=True))
        curr_y += 42

    # MRP (with customizable font size for font-ratio testing!)
    if mrp_text:
        draw.text((25, curr_y), f"MRP: {mrp_text}", fill=(15, 23, 42), font=get_font(mrp_font_size, bold=(mrp_font_size > 18)))
        curr_y += max(36, mrp_font_size + 14)

    # Date of Manufacture
    if mfg_text:
        draw.text((25, curr_y), f"Date of Mfg: {mfg_text}", fill=(15, 23, 42), font=get_font(20))
        curr_y += 38

    # Manufacturer details (multiline wrap)
    if mfr_text:
        draw.text((25, curr_y), "Mfg by: ", fill=(15, 23, 42), font=get_font(18, bold=True))
        # split if long
        draw.text((105, curr_y), mfr_text[:45], fill=(30, 41, 59), font=get_font(17))
        curr_y += 26
        if len(mfr_text) > 45:
            draw.text((105, curr_y), mfr_text[45:], fill=(30, 41, 59), font=get_font(17))
            curr_y += 32
        else:
            curr_y += 12

    # Consumer Care details
    if care_text:
        draw.rectangle([(20, curr_y), (width - 30, curr_y + 60)], fill=(238, 242, 255), outline=(199, 210, 254), width=1)
        draw.text((30, curr_y + 10), "Consumer Care Cell:", fill=(67, 56, 202), font=get_font(15, bold=True))
        draw.text((30, curr_y + 32), care_text, fill=(30, 27, 75), font=get_font(15))

    # Convert to OpenCV image
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # Blur simulation if requested (NFR-3)
    if blur:
        cv_img = cv2.GaussianBlur(cv_img, (31, 31), 0)

    cv2.imwrite(filename, cv_img)
    print(f"Generated sample: {filename}")

def generate_all_samples(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    # 1. Clean Compliant Pass
    create_sample_label(
        filename=os.path.join(output_dir, "sample_1_clean_pass.png"),
        brand_title="NUTRI-CRUNCH ALMOND COOKIES",
        product_subtitle="Baked Gourmet Biscuits with California Almonds",
        mrp_text="Rs. 120.00 (Incl. of all taxes)",
        mrp_font_size=24,  # Compliant font size >= baseline (22px)
        qty_text="250 g",
        mfg_text="09/2026",
        mfr_text="Healthy Bites Foodworks Ltd, Sector 18, Gurugram, Haryana - 122001",
        care_text="Toll Free: 18001124455, Email: care@healthybites.in"
    )

    # 2. Deliberate FAIL: Missing Manufacturing Date
    create_sample_label(
        filename=os.path.join(output_dir, "sample_2_fail_missing_mfg.png"),
        brand_title="FRESHCO TOMATO KETCHUP",
        product_subtitle="Farm Fresh Thick & Rich Tomato Sauce",
        mrp_text="Rs. 75.00 (Incl. of all taxes)",
        mrp_font_size=24,
        qty_text="500 g",
        mfg_text="",  # Deliberately missing!
        mfr_text="FreshCo Foods Pvt Ltd, Industrial Area, Pune, Maharashtra - 411028",
        care_text="Helpline: 9876543210, Email: feedback@freshco.com"
    )

    # 3. Deliberate FAIL: Undersized MRP Font (Font Ratio Checker highlight)
    create_sample_label(
        filename=os.path.join(output_dir, "sample_3_fail_small_mrp_font.png"),
        brand_title="GLOW & SILK HERBAL SHAMPOO",
        product_subtitle="Nourishing Hair Care with Natural Extracts",
        mrp_text="Rs. 299.00 (Incl. of taxes)",
        mrp_font_size=11,  # VIOLATION: Tiny 11px font vs 22px baseline text!
        qty_text="400 ml",
        mfg_text="08/2026",
        mfr_text="Pure Herbal Botanicals, Solan, Himachal Pradesh - 173212",
        care_text="Toll Free: 18002008899, Email: customercare@glowsilk.in"
    )

    # 4. Deliberate FAIL: Missing Consumer Care
    create_sample_label(
        filename=os.path.join(output_dir, "sample_4_fail_missing_care.png"),
        brand_title="PREMIUM CHOCO WAFER BARS",
        product_subtitle="Rich Cocoa Layered Crispy Wafers",
        mrp_text="Rs. 60.00",
        mrp_font_size=22,
        qty_text="150 g",
        mfg_text="11/2026",
        mfr_text="Sweet Indulgence Confectioneries, Whitefield, Bengaluru - 560034",
        care_text=""  # Deliberately missing!
    )

    # 5. Deliberate WARNING: Blurry Image for NFR-3 Re-capture check
    create_sample_label(
        filename=os.path.join(output_dir, "sample_5_blurry_recapture.png"),
        brand_title="ORGANIC CLOVER HONEY",
        product_subtitle="100% Pure Raw Forest Honey",
        mrp_text="Rs. 350.00",
        mrp_font_size=22,
        qty_text="500 g",
        mfg_text="07/2026",
        mfr_text="Nature Gold Apiculture, Dehradun, Uttarakhand - 248001",
        care_text="Phone: 9812345678, info@naturegold.in",
        blur=True
    )

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "static", "samples")
    generate_all_samples(out_dir)
