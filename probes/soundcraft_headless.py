#!/usr/bin/env python3
"""Synthetic, no-device SoundCraft acceptance with independent PCM checks.

Runs on the Mac or the VAIO's Python 3.5. Uses only an explicitly supplied CLI
and new private fixtures; never plays, records, opens a GUI or reads user media.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import select
import struct
import subprocess
import tempfile
import time
import wave


def wav_read(path):
    """Read our exported PCM independently of SoundCraft's codec implementation."""
    data = path.read_bytes()
    assert data[:4] == b'RIFF' and data[8:12] == b'WAVE'
    pos, fmt, payload = 12, None, None
    while pos + 8 <= len(data):
        kind, size = struct.unpack_from('<4sI', data, pos)
        chunk = data[pos + 8:pos + 8 + size]
        if kind == b'fmt ':
            fmt = struct.unpack_from('<HHIIHH', chunk)
            if fmt[0] == 0xfffe:
                fmt = (struct.unpack_from('<H', chunk, 24)[0],) + fmt[1:]
        if kind == b'data':
            payload = chunk
        pos += 8 + size + (size & 1)
    assert fmt is not None and payload is not None
    tag, channels, rate, _, _, bits = fmt
    if tag == 3 and bits == 32:
        values = struct.unpack('<' + str(len(payload) // 4) + 'f', payload)
    elif tag == 1 and bits == 16:
        values = [x[0] / 32768.0 for x in struct.iter_unpack('<h', payload)]
    elif tag == 1 and bits == 24:
        values = [int.from_bytes(payload[i:i + 3], 'little', signed=True) / 8388608.0
                  for i in range(0, len(payload), 3)]
    else:
        raise AssertionError('Unexpected WAV format ' + repr(fmt))
    assert all(math.isfinite(v) for v in values)
    return rate, channels, [values[c::channels] for c in range(channels)]


def fixture(path, rate, frames, frequencies, amplitude):
    values = [[], []]
    raw = bytearray()
    for i in range(frames):
        for c, hz in enumerate(frequencies):
            sample = int(amplitude * 32767 * math.sin(2 * math.pi * hz * i / rate))
            raw.extend(struct.pack('<h', sample))
            values[c].append(sample / 32768.0)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(raw)
    return values


def compare(path, expected, tolerance):
    rate, channels, values = wav_read(path)
    assert rate == 48000 and channels == 2
    assert all(len(v) == 96000 for v in values)
    # Clip-edge anti-click fades are intentional; inspect the interior of each edit.
    indices = list(range(2048, 48000 - 2048)) + list(range(48000 + 2048, 96000 - 2048))
    error = max(abs(values[c][i] - expected[c][i]) for c in range(2) for i in indices)
    assert error < tolerance, (str(path), error, tolerance)
    return {'frames': len(values[0]), 'channels': channels, 'sample_rate': rate,
            'interior_max_absolute_error': error, 'tolerance': tolerance}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--parent', type=Path, required=True)
    args = parser.parse_args()
    base = Path(tempfile.mkdtemp(prefix='headless-', dir=str(args.parent))).resolve()
    env = dict(os.environ, XDG_CONFIG_HOME=str(base / 'config'),
               XDG_DATA_HOME=str(base / 'data'), XDG_CACHE_HOME=str(base / 'cache'))
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY'):
        env.pop(key, None)
    result = {'passed': False, 'fixture': str(base), 'checks': [],
              'no_display': all(k not in env for k in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY')),
              'no_audio_devices_opened': True, 'cli_sha256': hashlib.sha256(args.cli.read_bytes()).hexdigest()}
    p, serial = None, 0
    start = time.monotonic()
    log = (base / 'mcp-stderr.log').open('w')
    try:
        rate, frames = 48000, 96000
        a = fixture(base / 'tone-a.wav', rate, frames, (440, 880), 0.05)
        b = fixture(base / 'tone-b.wav', rate, frames, (660, 1320), 0.025)
        p = subprocess.Popen([str(args.cli), 'mcp', '--automation-read-root', str(base),
                              '--automation-write-root', str(base)], env=env,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                             universal_newlines=True, bufsize=1)

        def rpc(method, params):
            nonlocal serial
            serial += 1
            p.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': serial, 'method': method, 'params': params}) + '\n')
            p.stdin.flush()
            assert select.select([p.stdout], [], [], 90)[0], 'MCP timeout: ' + method
            reply = json.loads(p.stdout.readline())
            assert reply.get('id') == serial and 'error' not in reply, reply
            return reply['result']

        def tool(name, params=None):
            reply = rpc('tools/call', {'name': name, 'arguments': params or {}})
            assert not reply.get('isError'), reply
            text = next(c['text'] for c in reply['content'] if c['type'] == 'text')
            return json.loads(text)

        def cmd(name, params=None):
            return tool('execute', {'command': name, 'params': params or {}})

        def inspect():
            return tool('inspect_session', {'detail': 'full'})

        rpc('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                           'clientInfo': {'name': 'vaio-soundcraft-check', 'version': '1'}})
        tool('new_session', {'name': 'VAIO synthetic mix', 'sample_rate': rate})
        for label in ('a', 'b'):
            tool('import_audio', {'path': str(base / ('tone-' + label + '.wav')), 'at': 0})
        state = inspect()
        audio = [t for t in state['tracks'] if t['kind'] == 'audio']
        assert len(audio) == 2 and len(state['sources']) == 2
        assert all(s['loaded'] for s in state['sources'])
        aid, bid = audio[0]['id'], audio[1]['id']
        cmd('track.rename', {'track': aid, 'name': 'Tone A'})
        cmd('track.rename', {'track': bid, 'name': 'Tone B'})
        cmd('edit.select', {'tracks': [aid]})
        half_db = -6.020599913279624
        cmd('mix.volume', {'track': aid, 'db': half_db})
        cmd('edit.undo')
        assert abs(next(t for t in inspect()['tracks'] if t['id'] == aid)['volume_db']) < 1e-6
        cmd('edit.redo')
        cmd('edit.separate', {'tracks': [aid], 'at': 48000})
        pieces = next(t for t in inspect()['tracks'] if t['id'] == aid)['clips']
        assert len(pieces) == 2
        cmd('edit.undo')
        assert len(next(t for t in inspect()['tracks'] if t['id'] == aid)['clips']) == 1
        cmd('edit.redo')
        pieces = sorted(next(t for t in inspect()['tracks'] if t['id'] == aid)['clips'], key=lambda c: c['start'])
        cmd('edit.select', {'tracks': [aid], 'clips': [pieces[1]['id']]})
        cmd('clip.gain', {'clips': [pieces[1]['id']], 'db': half_db})
        expected = [[a[c][i] * (0.5 if i < 48000 else 0.25) + b[c][i]
                     for i in range(frames)] for c in range(2)]
        result['checks'].extend(['no-display confined MCP', 'two stereo WAV imports',
                                 'track gain undo/redo', 'clip split undo/redo', 'second-clip gain'])
        bounce = {'path': str(base / 'mix.wav'), 'format': 'wav', 'bit_depth': '32f',
                  'start': 0, 'end': frames, 'dither': False}
        cmd('file.bounce_mix', bounce)
        result['pcm_mix'] = compare(base / 'mix.wav', expected, 0.00002)
        tool('save_session', {'path': str(base / 'mix.scraft')})
        tool('new_session')
        opened = tool('open_session', {'path': str(base / 'mix.scraft')})
        assert not opened.get('missing'), opened
        state = inspect()
        assert len(state['sources']) == 2 and all(s['loaded'] for s in state['sources'])
        bounce['path'] = str(base / 'reopened.wav')
        cmd('file.bounce_mix', bounce)
        result['reopened_mix'] = compare(base / 'reopened.wav', expected, 0.00002)
        assert wav_read(base / 'mix.wav')[2] == wav_read(base / 'reopened.wav')[2]
        result['checks'].extend(['independent mixed PCM comparison', 'save/reopen with media', 'sample-identical reopened render'])
        bounce.update(path=str(base / 'mix.flac'), format='flac', bit_depth='16')
        cmd('file.bounce_mix', bounce)
        assert (base / 'mix.flac').read_bytes()[:4] == b'fLaC'
        subprocess.check_call([str(args.cli), 'convert', str(base / 'mix.flac'),
                               str(base / 'flac-decoded.wav'), '--bit-depth', '32f'], env=env,
                              stdout=log, stderr=log, timeout=90)
        result['flac_mix'] = compare(base / 'flac-decoded.wav', expected, 0.00006)
        subprocess.check_call([str(args.cli), 'convert', str(base / 'tone-a.wav'),
                               str(base / 'resampled.wav'), '--rate', '44100', '--bit-depth', '32f'],
                              env=env, stdout=log, stderr=log, timeout=90)
        rr, channels, vals = wav_read(base / 'resampled.wav')
        assert rr == 44100 and channels == 2 and abs(len(vals[0]) - 88200) <= 1
        assert max(abs(v) for v in vals[0]) < 0.06
        rms = math.sqrt(sum(v * v for v in vals[0][4096:-4096]) / len(vals[0][4096:-4096]))
        assert 0.03 < rms < 0.04, rms
        result['resample'] = {'sample_rate': rr, 'frames': len(vals[0]), 'left_rms': rms}
        result['checks'].extend(['FLAC encode/decode with independent PCM comparison', '48 kHz to 44.1 kHz resampling'])
        (base / 'truncated.wav').write_bytes(b'RIFF\x10\x00\x00\x00WAVEfmt ')
        bad = subprocess.run([str(args.cli), 'info', str(base / 'truncated.wav')], env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
        assert bad.returncode == 1 and 'panicked' not in bad.stderr, (bad.returncode, bad.stderr)
        result['checks'].append('malformed audio returns an ordinary error')
        result['session_summary'] = {'audio_tracks': 2, 'sources_loaded': 2,
                                     'tone_a_clips': len(next(t for t in state['tracks'] if t['id'] == aid)['clips'])}
        result['passed'] = True
    except BaseException as exc:
        result['error'] = repr(exc)
    finally:
        if p is not None:
            p.stdin.close()
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.terminate()
                p.wait(timeout=5)
        log.close()
        result['elapsed_seconds'] = round(time.monotonic() - start, 3)
        (base / 'headless-result.json').write_text(json.dumps(result, indent=2) + '\n')
        (args.parent / 'headless-result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
