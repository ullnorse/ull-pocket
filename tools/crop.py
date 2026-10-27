"""crop.py name x1 y1 x2 y2  (sheet mm; full.png is 10 px/mm) -> build/review/<name>.png"""
import sys
from PIL import Image
n,x1,y1,x2,y2=sys.argv[1],*map(float,sys.argv[2:6])
im=Image.open("build/review/full.png")
s=im.width/420.0
c=im.crop((int(x1*s),int(y1*s),int(x2*s),int(y2*s)))
c.save(f"build/review/{n}.png")
