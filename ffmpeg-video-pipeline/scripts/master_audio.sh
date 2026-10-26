#!/usr/bin/env bash
# master_audio.sh IN.wav OUT.wav [LUFS=-14] [TP=-2.5]
# Loudnorm 2 passadas (linear) + correção fina + limitador com oversampling, saída 48 kHz.
# Mesma lógica de junon-edit/junon_edit/render.py master_audio() (L423-453).
set -euo pipefail
IN=$1; OUT=$2; I=${3:--14}; TP=${4:--2.5}; LRA=11
J=$(ffmpeg -hide_banner -nostats -i "$IN" -af "loudnorm=I=$I:TP=$TP:LRA=$LRA:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p')
g(){ echo "$J" | python3 -c "import sys,json;print(json.load(sys.stdin)['$1'])"; }
TMP="${OUT%.*}.ln.wav"
ffmpeg -hide_banner -loglevel error -y -i "$IN" -af "loudnorm=I=$I:TP=$TP:LRA=$LRA:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,aresample=48000" -c:a pcm_f32le "$TMP"
M=$(ffmpeg -hide_banner -nostats -i "$TMP" -af ebur128 -f null - 2>&1 | awk '/^ *I:/{v=$2} END{print v}')
CORR=$(python3 -c "c=$I-($M);print(f'{c:.2f}' if abs(c)>0.3 else '0')")
LIM=$(python3 -c "print(f'{10**($TP/20):.4f}')")
PRE=""; [ "$CORR" != "0" ] && PRE="volume=${CORR}dB,"
ffmpeg -hide_banner -loglevel error -y -i "$TMP" -af "${PRE}aresample=192000,alimiter=limit=$LIM:attack=1:release=50:level=disabled,aresample=48000" -c:a pcm_s16le "$OUT"
rm -f "$TMP"
echo -n "master: correção=${CORR} dB | "; ffmpeg -hide_banner -nostats -i "$OUT" -af ebur128=peak=true -f null - 2>&1 | grep -E '^ +(I|Peak):' | tr -s ' ' | tr '\n' ' '; echo
