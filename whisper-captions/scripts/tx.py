#!/usr/bin/env python3
"""tx.py IN [--model small] [--lang pt|auto] [--fmt srt,vtt,json] [--beam 5] [--words]
Transcreve audio/video (qualquer coisa que o ffmpeg le) -> SRT/VTT. CPU int16 (int8 instável no box)."""
import argparse,subprocess,json,time,os,numpy as np
from faster_whisper import WhisperModel
p=argparse.ArgumentParser();p.add_argument("inp");p.add_argument("--model",default="small")
p.add_argument("--lang",default="pt");p.add_argument("--fmt",default="srt,vtt");p.add_argument("--beam",type=int,default=5)
p.add_argument("--words",action="store_true");p.add_argument("--threads",type=int,default=4);p.add_argument("--compute-type",default="int16");a=p.parse_args()
raw=subprocess.run(["ffmpeg","-nostdin","-v","error","-i",a.inp,"-vn","-f","s16le","-ac","1","-ar","16000","-"],capture_output=True,check=True).stdout
audio=np.frombuffer(raw,np.int16).astype(np.float32)/32768  # contorna bug PyAV19 metadata_errors
t0=time.time();m=WhisperModel(a.model,device="cpu",compute_type=a.compute_type,cpu_threads=a.threads)
segs,info=m.transcribe(audio,language=None if a.lang=="auto" else a.lang,beam_size=a.beam,vad_filter=True,word_timestamps=a.words)
segs=list(segs)
def ts(s,sep):ms=int(round(s*1000));h,ms=divmod(ms,3600000);mi,ms=divmod(ms,60000);se,ms=divmod(ms,1000);return f"{h:02}:{mi:02}:{se:02}{sep}{ms:03}"
base=os.path.splitext(a.inp)[0]+f".{a.model}"
f=a.fmt.split(",")
if "srt" in f:open(base+".srt","w").write("\n".join(f"{i}\n{ts(s.start,',')} --> {ts(s.end,',')}\n{s.text.strip()}\n" for i,s in enumerate(segs,1)))
if "vtt" in f:open(base+".vtt","w").write("WEBVTT\n\n"+"\n".join(f"{ts(s.start,'.')} --> {ts(s.end,'.')}\n{s.text.strip()}\n" for s in segs))
if "json" in f:json.dump([{"start":s.start,"end":s.end,"text":s.text,"words":[w._asdict() for w in (s.words or [])]} for s in segs],open(base+".json","w"),ensure_ascii=False,indent=1)
print(f"LANG={info.language} p={info.language_probability:.2f} dur={info.duration:.1f}s took={time.time()-t0:.1f}s segs={len(segs)} out={base}.*")
