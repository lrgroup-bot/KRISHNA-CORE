from __future__ import annotations
import argparse,json,struct,zlib
from pathlib import Path

PNG_SIG=b"\x89PNG\r\n\x1a\n"

def paeth(a,b,c):
    p=a+b-c;pa=abs(p-a);pb=abs(p-b);pc=abs(p-c)
    return a if pa<=pb and pa<=pc else b if pb<=pc else c

def read_png(path:Path):
    raw=path.read_bytes()
    if not raw.startswith(PNG_SIG):raise ValueError("not a PNG")
    pos=8;width=height=bit_depth=color_type=interlace=None;idat=[]
    while pos+8<=len(raw):
        n=struct.unpack(">I",raw[pos:pos+4])[0];typ=raw[pos+4:pos+8];data=raw[pos+8:pos+8+n];pos+=12+n
        if typ==b"IHDR":width,height,bit_depth,color_type,_,_,interlace=struct.unpack(">IIBBBBB",data)
        elif typ==b"IDAT":idat.append(data)
        elif typ==b"IEND":break
    if bit_depth!=8 or color_type not in (2,6):raise ValueError(f"unsupported PNG depth={bit_depth} color_type={color_type}")
    if interlace!=0:raise ValueError("interlaced PNG unsupported")
    bpp=3 if color_type==2 else 4;stride=width*bpp
    data=zlib.decompress(b"".join(idat))
    if len(data)!=(stride+1)*height:raise ValueError("PNG payload length mismatch")
    rows=[];prev=bytearray(stride);off=0
    for _ in range(height):
        f=data[off];off+=1;src=data[off:off+stride];off+=stride;cur=bytearray(stride)
        for i,x in enumerate(src):
            left=cur[i-bpp] if i>=bpp else 0;up=prev[i];up_left=prev[i-bpp] if i>=bpp else 0
            if f==0:v=x
            elif f==1:v=(x+left)&255
            elif f==2:v=(x+up)&255
            elif f==3:v=(x+((left+up)//2))&255
            elif f==4:v=(x+paeth(left,up,up_left))&255
            else:raise ValueError(f"unknown PNG filter {f}")
            cur[i]=v
        rows.append(cur);prev=cur
    return width,height,bpp,rows

def metrics(path:Path):
    w,h,bpp,rows=read_png(path)
    y0=int(h*.06);y1=int(h*.88);x0=int(w*.12);x1=int(w*.88)
    total=bright_chroma=bright=0;sum_luma=sum_luma2=0.0
    for y in range(y0,y1):
        row=rows[y]
        for x in range(x0,x1):
            i=x*bpp;r,g,b=row[i],row[i+1],row[i+2];mx=max(r,g,b);mn=min(r,g,b);lum=(r+g+b)/3.0
            total+=1;sum_luma+=lum;sum_luma2+=lum*lum
            if mx>=145 and lum>=80:bright+=1
            if mx>=120 and (mx-mn)>=38 and lum>=55:bright_chroma+=1
    mean=sum_luma/max(1,total);std=max(0.0,sum_luma2/max(1,total)-mean*mean)**.5
    chroma_ratio=bright_chroma/max(1,total)
    passed=bright_chroma>=1800 and chroma_ratio>=.001 and std>=16.0
    return {"width":w,"height":h,"roi_pixels":total,"bright_chromatic_pixels":bright_chroma,
            "bright_chromatic_ratio":round(chroma_ratio,6),"bright_pixels":bright,
            "bright_ratio":round(bright/max(1,total),6),"luma_mean":round(mean,3),
            "luma_std":round(std,3),"passed":passed}

def main():
    p=argparse.ArgumentParser(description="Fail closed if KRISHNA Mobile visual proof is effectively blank.")
    p.add_argument("png");args=p.parse_args()
    out=metrics(Path(args.png));print(json.dumps(out,indent=2))
    if not out["passed"]:raise SystemExit("KRISHNA mobile screenshot does not contain enough visible avatar/UI pixels")
    return 0

if __name__=="__main__":raise SystemExit(main())
