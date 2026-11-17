"""Optional artwork rebuild: pip install Pillow, then python make_icons.py."""
from pathlib import Path
import io,zipfile
from PIL import Image
ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    original=Image.open(ROOT/'logo.png').convert('RGB')
    # Trim surplus white margin; preserve the complete artwork and aspect ratio.
    bounds=original.convert('L').point(lambda value:255 if value<180 else 0).getbbox()
    if bounds:
        left,top,right,bottom=bounds
        side=max(right-left,bottom-top)+40
        cx=(left+right)/2;cy=(top+bottom)/2
        original=original.crop((round(cx-side/2),round(cy-side/2),round(cx+side/2),round(cy+side/2))).resize((1024,1024),Image.Resampling.LANCZOS)
    with zipfile.ZipFile(ROOT/'brand-assets.zip','w',zipfile.ZIP_DEFLATED) as archive:
        buffer=io.BytesIO();original.save(buffer,format='PNG');archive.writestr('logo.png',buffer.getvalue())
        for size in [16,32,48,72,96,128,144,152,180,192,256,384,512]:
            buffer=io.BytesIO();original.resize((size,size),Image.Resampling.LANCZOS).save(buffer,format='PNG');archive.writestr('icon-'+str(size)+'.png',buffer.getvalue())
        buffer=io.BytesIO();original.save(buffer,format='ICO',sizes=[(size,size) for size in [16,32,48,64,128,256]]);archive.writestr('favicon.ico',buffer.getvalue())
    print('Generated brand-assets.zip from logo.png')
