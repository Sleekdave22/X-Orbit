import io,unittest
from PIL import Image,ImageOps
from profile_images import normalize
class OrientationTest(unittest.TestCase):
 def test_all_exif_transforms_and_idempotence(self):
  for orientation in range(1,9):
   with self.subTest(orientation=orientation):
    image=Image.new('RGB',(32,20));image.paste('red',(0,0,16,10));image.paste('blue',(16,10,32,20));exif=Image.Exif();exif[274]=orientation
    out=io.BytesIO();image.save(out,format='PNG',exif=exif);raw=out.getvalue()
    expected=ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    result,mime=normalize(raw,'image/png');actual=Image.open(io.BytesIO(result))
    self.assertEqual(actual.size,expected.size);self.assertEqual(actual.tobytes(),expected.tobytes());self.assertEqual(normalize(result,mime)[0],result)
 def test_no_metadata_is_unchanged(self):
  out=io.BytesIO();Image.new('RGB',(20,32),'red').save(out,format='JPEG');raw=out.getvalue();self.assertEqual(normalize(raw,'image/jpeg')[0],raw)
