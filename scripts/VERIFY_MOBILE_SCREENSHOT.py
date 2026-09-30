from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path


PNG_SIG=b"\x89PNG\r\n\x1a\n"


def _paeth(a,b,c):
    p=a+b-c
    pa=abs(p-a);pb=abs(p-b);pc=abs(p-c)
    return a if pa<=pb and pa<=pc else (b if pb<=pc else c)


def decode_rgb(path:Path):
    raw=path.read_bytes()
    if not raw.startswith(PNG_SIG):
        raise ValueError("invalid PNG signature")
    pos=8;width=height=None;color_type=None;bit_depth=None;chunks=[]
    while pos+12<=len(raw):
        length=struct.unpack(">I",raw[pos:pos+4])[0]
        kind=raw[pos+4:pos+8]
        data=raw[pos+8:pos+8+length]
        pos+=12+length
        if kind==b"IHDR":
            width,height,bit_depth,color_type,_,_,_=struct.unpack(">IIBBBBB",data)
        elif kind==b"IDAT":
            chunks.append(data)
        elif kind==b"IEND":
            break
    if not width or not height or bit_depth!=8 or color_type not in (2,6):
        raise ValueError(f"unsupported PNG format: {width}x{height} depth={bit_depth} color={color_type}")
    bpp=3 if color_type==2 else 4
    scan=zlib.decompress(b"".join(chunks))
    stride=width*bpp
    rows=[];off=0;prev=bytearray(stride)
    for _ in range(height):
        f=scan[off];off+=1
        cur=bytearray(scan[off:off+stride]);off+=stride
        for i in range(stride):
            left=cur[i-bpp] if i>=bpp else 0
            up=prev[i]
            ul=prev[i-bpp] if i>=bpp else 0
            if f==1:cur[i]=(cur[i]+left)&255
            elif f==2:cur[i]=(cur[i]+up)&255
            elif f==3:cur[i]=(cur[i]+((left+up)//2))&255
            elif f==4:cur[i]=(cur[i]+_paeth(left,up,ul))&255
            elif f!=0:raise ValueError(f"unsupported PNG filter {f}")
        rows.append(cur);prev=cur
    return width,height,bpp,rows


def verify(path:Path):
    width,height,bpp,rows=decode_rgb(path)
    # Ignore status/navigation bars; verify the app's central WebView pixels.
    y0=max(1,int(height*0.08));y1=min(height-1,int(height*0.92))
    total=bright=colored=0
    sum_luma=0
    for y in range(y0,y1):
        row=rows[y]
        for x in range(width):
            p=x*bpp;r,g,b=row[p],row[p+1],row[p+2]
            mx=max(r,g,b);mn=min(r,g,b)
            total+=1;sum_luma+=(r+g+b)/3
            if mx>=28:bright+=1
            if mx-mn>=12 and mx>=20:colored+=1
    bright_ratio=bright/max(1,total)
    colored_ratio=colored/max(1,total)
    mean_luma=sum_luma/max(1,total)
    print(f"KRISHNA_MOBILE_PIXEL_PROOF {width}x{height} mean={mean_luma:.2f} bright={bright_ratio:.4f} colored={colored_ratio:.4f}")
    if mean_luma<3.0 or bright_ratio<0.01 or colored_ratio<0.003:
        raise SystemExit("mobile screenshot is visually blank/black; WebView pixels were not proven")
    return 0


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: VERIFY_MOBILE_SCREENSHOT.py <png>")
    raise SystemExit(verify(Path(sys.argv[1])))
