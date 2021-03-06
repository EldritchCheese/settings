#!/usr/bin/env python3

import os
import subprocess
import sys
import tempfile

import scipy
from moviepy.editor import VideoClip

def extract_arguments(pov_file):
    arguments = []
    for line in open(pov_file):
        line = line.strip()
        if (line.startswith('//') and
            not line.startswith('////')):
            arguments.append(line[2:].strip())
        elif line:
            break
    return arguments

def render_png(pov_file, args):
    args = args[:]
    unbuffer = ['stdbuf','-i0','-o0','-e0']
    command = ['povray','-D'] + args + [pov_file]
    print(' '.join(command))
    proc = subprocess.Popen(command, stderr=subprocess.PIPE)

    print()
    has_had_error = False
    while True:
        line = better_readline(proc.stderr)
        if not line:
            break

        if 'Error' in line:
            has_had_error = True

        if (has_had_error or
            any(line.startswith(key) for key in ['Rendered','Photon']) ):
            print(line,end='')
    print()


def better_readline(stream):
    '''
    readline() can either split on \n only,
      or with universal_newlines, can split on \r and convert it to \n.
    I want to split on either \r or \n, maintaining which was sent.
    '''
    line_chars = []
    while True:
        char = stream.read(1).decode('ascii')
        if char:
            line_chars.append(char)
        if char in ['\r','\n','']:
            break
    return ''.join(line_chars)


def frame_gen(pov_file, args, initial_time=0, time_scaling=1.0):

    def make_frame(time):
        actual_time = time*time_scaling + initial_time
        all_args = ['Clock={}'.format(actual_time)] + args

        with tempfile.TemporaryDirectory() as workdir:
            tmp_pov = os.path.join(workdir, 'file.pov')
            os.symlink(os.path.realpath(pov_file), tmp_pov)
            render_png(tmp_pov, all_args)
            tmp_png = tmp_pov.replace('.pov','.png')
            return scipy.ndimage.imread(tmp_png)

    return make_frame

def render_gif(pov_file, args):
    prog_args = []

    clock_args = {'fps': None,
                  'initial_clock': 0,
                  'final_clock': None,
                  'initial_frame': 0,
                  'final_frame': None,
                  }

    for arg in args:
        if '=' in arg:
            key,value = arg.split('=')
            key = key.strip().lower()
            if key in clock_args:
                clock_args[key] = float(value)
            else:
                prog_args.append(arg)
        else:
            prog_args.append(arg)


    FPS = clock_args['fps']
    initial_clock = clock_args['initial_clock']
    final_clock = clock_args['final_clock']
    initial_frame = clock_args['initial_frame']
    final_frame = clock_args['final_frame']
    time_scaling = 1.0

    if (FPS is not None and
        final_clock is not None and
        final_frame is not None):
        would_be_FPS = (final_frame-initial_frame) / (final_clock-initial_clock)
        time_scaling = FPS / would_be_FPS

    if FPS is None:
        if (final_clock is not None and
            final_frame is not None):
            FPS = (final_clock-initial_clock) / (final_frame-initial_frame)
        else:
            raise ValueError('FPS must be set at top of file')

    if final_clock is None:
        if (FPS is not None and
            final_frame is not None):
            final_clock = initial_clock + (final_frame-initial_frame)/FPS
        else:
            raise ValueError('Final_Clock must be set at top of file')

    if final_frame is None:
        if (FPS is not None and
            final_clock is not None):
            final_frame = initial_frame + (final_clock-initial_clock)*FPS
        else:
            raise ValueError('Final_Frame must be set at top of file')


    make_frame = frame_gen(pov_file, prog_args, initial_clock, time_scaling)
    clip = VideoClip(make_frame, duration=(final_clock-initial_clock)/time_scaling)
    # output_gif = pov_file.replace('.pov','.gif')
    # clip.write_gif(output_gif, fps=FPS,
    #                program='ffmpeg')
    output_mp4 = pov_file.replace('.pov','.mp4')
    clip.write_videofile(output_mp4, fps=FPS,
                         codec='libx264', bitrate='500k',
                         audio=False)
    print('')


def render(pov_file):
    args = extract_arguments(pov_file)
    needs_gif = any(keyword in ' '.join(args).lower()
                    for keyword in ['fps','initial_clock','final_clock'])

    if needs_gif:
        render_gif(pov_file, args)
    else:
        render_png(pov_file, args)

if __name__=='__main__':
    render(sys.argv[1])
