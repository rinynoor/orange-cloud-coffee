from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import wave
import subprocess

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
for i in range(1, 6):
    if not (ASSETS / f'shot_{i:02d}.png').exists():
        raise FileNotFoundError(f'Missing assets/shot_{i:02d}.png')

W, H = 720, 1280
def font_path(kind):
    candidates = {
        'serif': ['/System/Library/Fonts/Supplemental/Georgia.ttf', 'C:/Windows/Fonts/georgia.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'],
        'sans': ['/System/Library/Fonts/Supplemental/Arial.ttf', 'C:/Windows/Fonts/arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'],
        'bold': ['/System/Library/Fonts/Supplemental/Arial Bold.ttf', 'C:/Windows/Fonts/arialbd.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'],
    }
    for candidate in candidates[kind]:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(f'No supported {kind} font was found; adjust font_path() for your system.')

serif, sans, bold = (font_path(kind) for kind in ('serif', 'sans', 'bold'))

def centered(draw, y, line, font, fill):
    box = draw.textbbox((0, 0), line, font=font)
    draw.text(((W - (box[2] - box[0])) / 2, y), line, font=font, fill=fill,
              stroke_width=1, stroke_fill=(42, 31, 24, 170))

for i, word in enumerate(['FRESH', 'CHILL', 'POUR', 'CLOUD'], 1):
    im = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(sans, 25)
    centered(d, 120, word, f, (255, 248, 232, 245))
    d.line((W/2 - 42, 168, W/2 + 42, 168), fill=(254, 185, 100, 220), width=2)
    im.save(ASSETS / f'type_{i:02d}.png')

im = Image.new('RGBA', (W, H))
d = ImageDraw.Draw(im)
d.rounded_rectangle((67, 77, W-67, 315), radius=15, fill=(29, 20, 15, 129))
centered(d, 105, 'ORANGE', ImageFont.truetype(serif, 60), (255, 247, 223, 255))
centered(d, 173, 'CLOUD COFFEE', ImageFont.truetype(bold, 35), (255, 247, 223, 255))
d.line((W/2 - 77, 236, W/2 + 77, 236), fill=(245, 161, 82, 255), width=3)
centered(d, 263, 'Coffee. Citrus. Unexpected.', ImageFont.truetype(sans, 23), (255, 247, 223, 255))
im.save(ASSETS / 'final_typography.png')

# Original synthesized sound design: morning room tone, citrus cut, ice,
# espresso stream, gentle foam hiss. No sampled audio or music.
rate, duration = 44100, 15
rng = np.random.default_rng(54)
n = rate * duration
sound = np.zeros(n, dtype=np.float64)
def place(start, data, volume):
    off = int(start * rate)
    length = min(len(data), n-off)
    if length > 0: sound[off:off+length] += data[:length] * volume
def decaying_ping(seconds, freq, decay):
    t = np.arange(int(rate*seconds))/rate
    return np.sin(2*np.pi*freq*t) * np.exp(-t*decay)
def noise_swish(seconds, decay=5):
    t = np.arange(int(rate*seconds))/rate
    raw = rng.normal(0, 1, len(t))
    smooth = np.convolve(raw, np.ones(9)/9, mode='same')
    return smooth * np.exp(-t*decay)
room = rng.normal(0, 1, n)
room = np.convolve(room, np.ones(161)/161, mode='same')
sound += room * .045
place(.46, noise_swish(.7, 6), .33)
place(.57, decaying_ping(.13, 1200, 30), .065)
for t, f in [(3.33, 1720), (3.64, 1310), (3.94, 1870), (4.26, 1520)]:
    place(t, decaying_ping(.58, f, 10), .095)
    place(t, noise_swish(.32, 14), .13)
start, length = 6.25, 3.45
t = np.arange(int(rate*length))/rate
flow = rng.normal(0, 1, len(t))
flow = np.convolve(flow, np.ones(17)/17, mode='same')
env = np.minimum(1, t*3) * np.minimum(1, (length-t)*3)
place(start, flow*env, .42)
place(9.15, noise_swish(1.25, 2.4), .17)
for t,f in [(12.1, 550), (12.15, 830)]:
    place(t, decaying_ping(2.7,f,2.4), .017)
fade = np.minimum(1, np.arange(n)/(rate*.3))*np.minimum(1,(n-np.arange(n))/(rate*.7))
sound *= fade
sound /= max(1, np.max(np.abs(sound))/.70)
pcm = (sound*32767).astype('<i2')
with wave.open(str(ASSETS/'sound_design.wav'), 'wb') as out:
    out.setnchannels(1); out.setsampwidth(2); out.setframerate(rate); out.writeframes(pcm.tobytes())

input_args=[]
for i in range(1,6):
    input_args += ['-loop','1','-framerate','24','-i',str(ASSETS/f'shot_{i:02d}.png')]
for i in range(1,5):
    input_args += ['-loop','1','-framerate','24','-i',str(ASSETS/f'type_{i:02d}.png')]
input_args += ['-loop','1','-framerate','24','-i',str(ASSETS/'final_typography.png'),'-i',str(ASSETS/'sound_design.wav')]
filters=[]
for i in range(5):
    # Gentle continuous camera push, with the last shot pulling back slightly.
    zoom = "max(1.0,1.07-0.0009*on)" if i==4 else "min(1.09,1.0+0.0011*on)"
    filters.append(f'[{i}:v]scale=760:1352,zoompan=z=\'{zoom}\':x=\'(iw-iw/zoom)/2\':y=\'(ih-ih/zoom)/2\':d=77:s=720x1280:fps=24,trim=duration=3.208333,setpts=PTS-STARTPTS,format=yuv420p[v{i}]')
last='v0'
for i in range(1,5):
    out=f'x{i}'
    filters.append(f'[{last}][v{i}]xfade=transition=fade:duration=0.25:offset={i*2.958333:.6f}[{out}]')
    last=out
for i in range(4):
    filters.append(f'[{i+5}:v]scale=720:1280,format=rgba,trim=duration=15,setpts=PTS-STARTPTS[t{i}]')
    out=f'o{i}'
    filters.append(f'[{last}][t{i}]overlay=0:0:enable=\'between(t,{i*2.958333+.25:.3f},{(i+1)*2.958333-.20:.3f})\'[{out}]')
    last=out
filters.append('[9:v]scale=720:1280,format=rgba,trim=duration=15,setpts=PTS-STARTPTS[title]')
filters.append(f'[{last}][title]overlay=0:0:enable=\'gte(t,12.15)\',trim=duration=15,format=yuv420p[final]')
cmd=['ffmpeg','-hide_banner','-loglevel','error','-y',*input_args,'-filter_complex',';'.join(filters),'-map','[final]','-map','10:a','-t','15','-r','24','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(ROOT/'Orange_Cloud_Coffee_15s.mp4')]
subprocess.run(cmd, check=True)
