"""montage.py out.png in1.png in2.png ... : paste images in a grid (max width 2400)."""
import sys
from PIL import Image
ims=[Image.open(p).convert("RGB") for p in sys.argv[2:]]
W=2400; x=y=rowh=0; pos=[]
for im in ims:
    if x+im.width>W and x>0: x=0; y+=rowh+20; rowh=0
    pos.append((x,y)); x+=im.width+20; rowh=max(rowh,im.height)
H=y+rowh
out=Image.new("RGB",(W,H),"white")
for im,p in zip(ims,pos): out.paste(im,p)
out.save(sys.argv[1])
