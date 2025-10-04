from flask import Flask, render_template, request, send_file
import pdfplumber, io
from reportlab.pdfgen import canvas
from reportlab.lib.colors import white, black
from reportlab.pdfbase import pdfmetrics
from PyPDF2 import PdfReader, PdfWriter

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        pdf_file = request.files["pdf"]
        numbers_file = request.files["numbers"]

        # Load replacement numbers
        replacements = [line.strip() for line in numbers_file if line.strip()]

        # Read original PDF
        reader = PdfReader(pdf_file)
        writer = PdfWriter()

        positions = []
        rep_index = 0
        start_replacing = False

        # Find FORECAST positions
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages):
                width, height = page.width, page.height
                words = page.extract_words()
                for w in words:
                    if w["text"] == "PO" or w["text"] == "Number":
                        start_replacing = True
                    if start_replacing and w["text"] == "FORECAST" and rep_index < len(replacements):
                        positions.append((page_num, width, height, w["x0"], w["x1"], w["top"], replacements[rep_index]))
                        rep_index += 1

        # Create overlay in memory
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(width, height))
        font_name, font_size, y_shift = "Helvetica", 9, -1.5
        c.setFont(font_name, font_size)

        for page_num, pw, ph, x0, x1, y, new_text in positions:
            y_coord = ph - y + y_shift
            original_width = x1 - x0
            new_width = pdfmetrics.stringWidth(new_text, font_name, font_size)
            centered_x = x0 + (original_width - new_width) / 2

            # White rectangle to hide "FORECAST"
            c.setFillColor(white)
            c.rect(
                x0 - 1,
                y_coord - font_size + 2,
                original_width + 2,
                font_size + 3,
                fill=1,
                stroke=0
            )

            # Draw replacement number
            c.setFillColor(black)
            c.drawString(centered_x, y_coord, new_text)

        c.save()
        packet.seek(0)
        overlay = PdfReader(packet)

        # Merge overlay into original
        for i in range(len(reader.pages)):
            page = reader.pages[i]
            if i < len(overlay.pages):
                page.merge_page(overlay.pages[0])
            writer.add_page(page)

        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)

        return send_file(output_stream, as_attachment=True, download_name="output.pdf")

    return render_template("index.html")

if __name__ == "__main__":
    # Render requires listening on 0.0.0.0:5000
    app.run(host="0.0.0.0", port=5000)

