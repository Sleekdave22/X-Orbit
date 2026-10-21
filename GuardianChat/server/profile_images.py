"""Normalize new avatars before metadata is removed; existing stored photos are untouched."""
import io
from PIL import Image, ImageOps

def normalize(raw,mime):
 with Image.open(io.BytesIO(raw)) as image:
  if image.format not in ('JPEG','PNG'):raise ValueError('Choose a JPEG or PNG profile picture')
  if image.width*image.height>16_000_000:raise ValueError('Profile picture is too large')
  oriented=ImageOps.exif_transpose(image)
  # Preserve already normalized uploads byte for byte, including their quality.
  if image.getexif().get(274,1)==1:return raw,mime
  out=io.BytesIO()
  if image.format=='JPEG':oriented.convert('RGB').save(out,format='JPEG',quality=95)
  else:oriented.save(out,format='PNG')
  result=out.getvalue()
  if len(result)>256*1024:raise ValueError('Choose a smaller profile picture')
  return result,mime
