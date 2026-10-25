"""Verified white raster is blank; nonwhite raster requires real OCR."""
import sys
import types
import unittest
from unittest.mock import patch

from suryadev_book_reader import default_pdf_ocr, VERIFIED_BLANK_PDF_PAGE


class FakeImage:
    def __init__(self, white):
        self.white=white
    def convert(self, mode):
        assert mode=="RGB"
        return self
    def getextrema(self):
        return ((255,255),(255,255),(255,255)) if self.white else (
            (0,255),(0,255),(0,255))


class FakePage:
    def __init__(self, white):
        self.white=white
    def render(self, scale):
        assert scale==2
        return self
    def to_pil(self):
        return FakeImage(self.white)


class PDF:
    def __init__(self,*args,**kwargs):
        self.closed=False
        self.white=True
    def __getitem__(self,index):
        assert index==1
        return FakePage(self.white)
    def close(self):
        self.closed=True


class PdfBlankOcrTests(unittest.TestCase):
    def test_white_raster_is_verified_without_tesseract(self):
        pdf=PDF()
        with patch.dict(sys.modules,{"pypdfium2":types.SimpleNamespace(
                PdfDocument=lambda _:pdf)}):
            result=default_pdf_ocr("known-source.pdf",2)
        self.assertIs(result,VERIFIED_BLANK_PDF_PAGE)
        self.assertTrue(pdf.closed)

    def test_nonwhite_image_requires_ocr(self):
        pdf=PDF()
        pdf.white=False
        count=[]
        ocr=types.SimpleNamespace(
            image_to_string=lambda img:count.append(img) or "Visible diagram label",
            TesseractNotFoundError=RuntimeError)
        with patch.dict(sys.modules,{"pypdfium2":types.SimpleNamespace(
                PdfDocument=lambda _:pdf),"pytesseract":ocr}):
            result=default_pdf_ocr("known-source.pdf",2)
        self.assertEqual(result,"Visible diagram label")
        self.assertEqual(len(count),1)
        self.assertTrue(pdf.closed)

    def test_empty_nonwhite_ocr_is_not_blank_proof(self):
        pdf=PDF()
        pdf.white=False
        ocr=types.SimpleNamespace(image_to_string=lambda img:"",
                                  TesseractNotFoundError=RuntimeError)
        with patch.dict(sys.modules,{"pypdfium2":types.SimpleNamespace(
                PdfDocument=lambda _:pdf),"pytesseract":ocr}):
            result=default_pdf_ocr("known-source.pdf",2)
        self.assertEqual(result,"")
        self.assertIsNot(result,VERIFIED_BLANK_PDF_PAGE)


if __name__=="__main__":
    unittest.main()
