"""Generate a synthetic clinical document image for testing.

Creates a PNG image with fake but realistic clinical text containing
various PHI types (names, dates, SSN, MRN, phone, fax, address, email, etc.).
"""

import os

from PIL import Image, ImageDraw, ImageFont

SAMPLE_CLINICAL_TEXT = """PATIENT: John Michael Smith
DATE OF BIRTH: 03/15/1958
DATE OF SERVICE: 01/22/2025
MRN: 78456123

FACILITY: Sunrise Rehabilitation Hospital
ADDRESS: 4521 Oak Valley Drive, Springfield, IL 62704
PHONE: (217) 555-0142
FAX: (217) 555-0199

REFERRING PHYSICIAN: Dr. Sarah Elizabeth Johnson, MD
NPI: 1234567890

INSURANCE: BlueCross BlueShield
Member ID: BCB9876543210
Group Number: GRP-44521

CHIEF COMPLAINT:
Patient presents for follow-up evaluation of low back pain status post
lumbar fusion surgery performed on 11/08/2024.

SUBJECTIVE:
Mr. Smith reports improvement in radicular symptoms since surgery.
Current pain level 4/10, down from 8/10 pre-operatively.
He is able to ambulate with a rolling walker for household distances.
Patient denies bowel or bladder dysfunction.

OBJECTIVE:
Vitals: BP 128/82, HR 72, Temp 98.4F
Lumbar incision well-healed, no erythema or drainage.
Strength: L hip flexion 4/5, L knee extension 4+/5, L ankle DF 4/5.
Sensation intact to light touch in all dermatomes.
SLR negative bilaterally.

ASSESSMENT:
1. Status post L4-L5 lumbar fusion (CPT 22612) - improving
2. Lumbar radiculopathy, left L5 distribution (ICD-10 M54.17)
3. Deconditioning secondary to post-operative activity restrictions

PLAN:
1. Continue physical therapy 3x/week for 4 weeks
2. Progress weight bearing as tolerated
3. Follow up in 4 weeks with repeat imaging
4. Patient SSN on file: 412-68-7935
5. Account #: 845612

Email: john.smith.patient@email.com
Emergency Contact Phone: (217) 555-0188"""


def generate_fixture(output_dir: str = "tests/fixtures"):
    """Render clinical text onto a white image and save as PNG."""
    os.makedirs(output_dir, exist_ok=True)

    # Create a white canvas
    width, height = 1200, 1800
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Use default font (monospace-like)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 16)
    except (OSError, IOError):
        font = ImageFont.load_default()

    # Draw text line by line
    y = 30
    for line in SAMPLE_CLINICAL_TEXT.strip().split("\n"):
        draw.text((40, y), line, fill="black", font=font)
        y += 22

    output_path = os.path.join(output_dir, "sample_clinical.png")
    img.save(output_path)
    print(f"Generated test fixture: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_fixture()
