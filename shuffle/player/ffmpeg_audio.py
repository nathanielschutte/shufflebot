import discord
import subprocess
import threading
import asyncio
import logging
import shlex

class BetterFFmpegPCMAudio(discord.AudioSource):
    """A more robust implementation of FFmpegPCMAudio that handles errors better."""
    
    def __init__(self, source, *, executable='ffmpeg', pipe=False, stderr=None, 
                 before_options=None, options=None, logger=None):
        self.source = source
        self.executable = executable
        self.pipe = pipe
        self.stderr = stderr
        self.before_options = before_options
        self.options = options
        self.logger = logger or logging.getLogger(__name__)
        
        self._process = None
        self._stderr_thread = None
        self._stdout_thread = None
        self._buffer = bytearray()
        self._error = None
        self._end = threading.Event()
        self._has_data = threading.Event()
        
        args = self._get_args()
        self._try_start_process(args)
        
    def _get_args(self):
        args = [self.executable]
        
        if self.before_options:
            args.extend(shlex.split(self.before_options))
            
        args.append('-i')
        args.append(self.source)
        args.append('-f')
        args.append('s16le')
        args.append('-ar')
        args.append('48000')
        args.append('-ac')
        args.append('2')
        args.append('pipe:1')
        
        if self.options:
            args.extend(shlex.split(self.options))
            
        return args
    
    def _try_start_process(self, args):
        try:
            self.logger.debug(f'Starting FFmpeg process with args: {" ".join(args)}')
            self._process = subprocess.Popen(
                args, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE if self.stderr else subprocess.DEVNULL
            )
            
            if self.stderr:
                self._stderr_thread = threading.Thread(
                    target=self._stderr_reader,
                    daemon=True
                )
                self._stderr_thread.start()
                
            self._stdout_thread = threading.Thread(
                target=self._stdout_reader,
                daemon=True
            )
            self._stdout_thread.start()
            
        except Exception as e:
            self.logger.error(f'Error starting FFmpeg process: {str(e)}')
            self._error = e
            self._end.set()
            
    def _stderr_reader(self):
        while self._process and not self._end.is_set():
            line = self._process.stderr.readline()
            if not line:
                break
                
            try:
                line = line.decode('utf-8')
                self.logger.debug(f'FFmpeg stderr: {line.strip()}')
            except:
                pass
                
    def _stdout_reader(self):
        chunk_size = 4096  # Adjust as needed
        
        while self._process and not self._end.is_set():
            try:
                chunk = self._process.stdout.read(chunk_size)
                
                if not chunk:
                    self._end.set()
                    break
                    
                with threading.Lock():
                    self._buffer.extend(chunk)
                    self._has_data.set()
                    
            except Exception as e:
                self.logger.error(f'Error reading from FFmpeg stdout: {str(e)}')
                self._error = e
                self._end.set()
                break
                
    def read(self):
        if self._error:
            raise self._error
            
        if self._end.is_set() and not self._buffer:
            return b''
            
        # Wait for data (with timeout to prevent hanging)
        if not self._buffer:
            self._has_data.wait(timeout=5)
            
        # Check again after waiting
        if not self._buffer:
            if self._process and self._process.poll() is not None:
                self._end.set()
            return b''
            
        # Read 3840 bytes (20ms of stereo audio at 48kHz)
        with threading.Lock():
            data = bytes(self._buffer[:3840])
            del self._buffer[:len(data)]
            
            if not self._buffer:
                self._has_data.clear()
                
        return data
        
    def cleanup(self):
        self._end.set()
        
        if self._process:
            try:
                self._process.kill()
            except:
                pass
                
        self._buffer.clear()
