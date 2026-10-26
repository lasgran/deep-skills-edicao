#!/bin/bash
# Smoke test das receitas do SKILL-DRAFT. Fixture própria (sintética), 4 s.
set -u; cd "$(dirname "$0")"; mkdir -p /tmp/ffsmoke; cp master_audio.sh /tmp/ffsmoke/; cd /tmp/ffsmoke; F="nice -n 10 ffmpeg -hide_banner -loglevel error -y"
pass=0; fail=0
chk(){ n=$1; f=$2; exp=$3; got=$(ffprobe -v error -show_entries stream=codec_type,width,height,codec_name -show_entries format=duration -of compact=p=0:nk=1 "$f" 2>&1 | tr '\n' ' ');
 if ffmpeg -v error -i "$f" -f null - 2>/dev/null && echo "$got" | grep -q -- "$exp"; then echo "PASS $n | $got"; pass=$((pass+1)); else echo "FAIL $n | $got"; fail=$((fail+1)); fi; }
# fixture
$F -f lavfi -i testsrc2=s=1280x720:r=30:d=4 -f lavfi -i sine=f=440:d=4 -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest fx.mp4
$F -f lavfi -i sine=f=880:d=4 -c:a pcm_s16le music.wav
printf '1\n00:00:00,500 --> 00:00:02,000\nOlá, ação!\n\n2\n00:00:02,200 --> 00:00:03,800\nSegunda legenda\n' > subs.srt
# 1 remux mp4->mkv sem reencode
$F -i fx.mp4 -c copy -map 0 r1_remux.mkv; chk remux r1_remux.mkv "h264"
# 2 scale 720p->480 mantendo aspecto, par
$F -i fx.mp4 -vf "scale=-2:480" -c:v libx264 -crf 23 -preset veryfast -c:a copy r2_scale.mp4; chk scale r2_scale.mp4 "854|480"
# 3 Shorts 9:16 crop central 1080x1920
$F -i fx.mp4 -vf "crop=ih*9/16:ih,scale=1080:1920,setsar=1" -c:v libx264 -preset faster -crf 19 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -movflags +faststart r3_short_crop.mp4; chk short_crop r3_short_crop.mp4 "1080|1920"
# 4 Shorts 9:16 com fundo desfocado (sem cortar)
$F -i fx.mp4 -filter_complex "[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=30[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]" -map "[v]" -map 0:a -c:v libx264 -crf 20 -preset veryfast -pix_fmt yuv420p -c:a aac -movflags +faststart r4_short_blur.mp4; chk short_blur r4_short_blur.mp4 "1080|1920"
# 5 legenda queimada (hard) com estilo
$F -i fx.mp4 -vf "subtitles=subs.srt:force_style='FontName=DejaVu Sans,FontSize=24,Outline=2,Alignment=2,MarginV=40'" -c:v libx264 -crf 20 -preset veryfast -c:a copy r5_burn.mp4; chk burn_subs r5_burn.mp4 "h264"
# 6 legenda soft (mov_text) sem reencode
$F -i fx.mp4 -i subs.srt -map 0 -map 1 -c copy -c:s mov_text -metadata:s:s:0 language=por r6_softsub.mp4; chk soft_subs r6_softsub.mp4 "mov_text"
# 7 amix voz + música (música a 20%), duração da voz
$F -i fx.mp4 -i music.wav -filter_complex "[1:a]volume=0.2[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k r7_amix.mp4; chk amix r7_amix.mp4 "aac"
# 8 loudnorm -14 LUFS (YouTube/Shorts)
$F -i r7_amix.mp4 -vn -c:a pcm_s16le r8_mix.wav && bash ./master_audio.sh r8_mix.wav r8_master.wav >/dev/null && $F -i r7_amix.mp4 -i r8_master.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 r8_loud.mp4; chk loudnorm2p r8_loud.mp4 "aac"
# 11 preview 540x960 ultrafast CRF26
$F -i r3_short_crop.mp4 -vf scale=540:960 -c:v libx264 -preset ultrafast -crf 26 -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart r11_preview.mp4; chk preview r11_preview.mp4 "540|960"
# 9 corte preciso (reencode) 1s..3s
$F -ss 1 -i fx.mp4 -t 2 -c:v libx264 -crf 20 -preset veryfast -c:a aac r9_cut.mp4; chk cut r9_cut.mp4 "2.0"
# 10 thumbnail 1280x720 no segundo 2
$F -ss 2 -i fx.mp4 -frames:v 1 -q:v 2 r10_thumb.jpg; chk thumb r10_thumb.jpg "1280|720"
echo "TOTAL pass=$pass fail=$fail"
# medição de volume do amix/loudnorm
for f in fx.mp4 r7_amix.mp4 r8_loud.mp4; do echo -n "$f "; ffmpeg -hide_banner -i $f -af ebur128 -f null - 2>&1 | grep -E '^\s+I:' | tail -1; done
