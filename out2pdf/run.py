# coding: cp1251
import os
import multiprocessing
import traceback
import sys
import datetime
import Queue
import codecs
import shutil

from task import *
from preprocess import (preprocess, PreprocessException)
import tex

with open(AIRPORT_FILE, 'r') as f:
    APT_CODES = f.read().split()

PROC_ID = 0
LOG_FILE = None

def log_output(data):
    sys.stdout.write("(%d) %s" % (PROC_ID, data))
    LOG_FILE.write(data.encode(sys.stdout.encoding, errors='replace'))


MOSCOW_APTS = ('UUDD', 'UUWW', 'UUEE')
    
def process_file(data_fname, is_takeoff, ac_eng, apt_code, tex_src, is_last):
    data, metadata = preprocess(data_fname, ac_eng, apt_code, is_takeoff)
    tex.update_xelatex_src(tex_src, apt_code, data, metadata, is_last=is_last)


def process_folders(ac_eng_folder, task, ac_eng, type):
    cwd = os.getcwd()
    os.chdir(ac_eng_folder)

    (folders, group_folder) = task
    
    log_output("'%s' %s started.\n" % (ac_eng_folder, ' / '.join(folders)))
    t0 = datetime.datetime.now()

    try:
        pdf_folder = group_folder + '_PDF'
        temp_folder = group_folder + '_AUX'
        for f in [pdf_folder, temp_folder]:
            if not os.path.exists(f): os.makedirs(f)
        
        pdf_fname_template = PDF_NAME_TEMPLATES[group_folder]
        for apt_code in APT_CODES:
            tex_src = tex.init_xelatex_src()
            for i, case_folder in enumerate(folders):
                data_fname = os.path.join(case_folder, apt_code + '.out')
                process_file(
                    data_fname, type == 'takeoff',
                    ac_eng, apt_code, tex_src, is_last=(i == len(folders) - 1))
            
            pdf_basename = os.path.basename(pdf_fname_template % dict(ac_eng=ac_eng, code=apt_code))
    
            if apt_code in MOSCOW_APTS:
                pdf_basename = '_' + pdf_basename
            tex_fname = os.path.join(temp_folder, pdf_basename[:-4] + '.tex')
            with open(tex_fname, 'w') as f:
                codecs.getwriter('utf-8')(f).writelines(tex_src)

            tex.compile_xelatex(tex_fname, pdf_folder, temp_folder)

        shutil.rmtree(temp_folder)
    finally:
        os.chdir(cwd)
    
    delta_time = datetime.datetime.now() - t0
    log_output("'%s' %s finished. Time taken: %s.\n" % (ac_eng_folder, ' / '.join(folders), str(delta_time)))
    
 
def process(id, queue, error_queue):
    global PROC_ID, LOG_FILE

    try:
        PROC_ID = id
        LOG_FILE = open('out2pdf-%d.log' % id, 'w')
        
        while True:
            args = queue.get(True, 1)
            if args is None:
                log_output('Nothing to do.\n')
                break
            process_folders(**args)

    except KeyboardInterrupt:
        log_output('Terminating.\n')
    except tex.MikTexException as e:
        log_output(e.message)
        log_output('Stdout:\n')
        log_output(e.stdout)
        log_output('Stderr:\n')
        log_output(e.stderr)
        log_output('Terminating.\n')
    except Queue.Empty:
        log_output('Terminating due to empty queue.\n')
    except:
        log_output('An error occured:\n')
        log_output(traceback.format_exc())
        try:
            error_queue.put(id, True, 2)
        except Queue.Full:
            # If error queue is full, we have nothing to complain about
            pass
    finally:
        LOG_FILE.close()
        

ERROR_PRESENT = False
def check_error(error_queue):
    global ERROR_PRESENT
    try:
        id = error_queue.get_nowait()
        log_output('Error in process %d.\n' % id)
        ERROR_PRESENT = True
        raise KeyboardInterrupt
    except Queue.Empty:
        pass
        
def enqueue_and_check(queue, error_queue, args):
    while True:
        check_error(error_queue)
        try:
            queue.put(args, True, 1)
            break
        except Queue.Full:
            pass
        

        
def finalize(processes, error_queue, force=False):
    if force:
        log_output('Finalizing...\n')
    else:
        log_output('Waiting for all to finish...\n')
    
    timeout = 0.2
    wait = True
    while wait:
        wait = False
        for p in processes:
            p.join(timeout)
            if force and p.is_alive():
                log_output('Terminating %s.\n' % str(p))
                p.terminate()
            elif p.is_alive():
                wait = True
            if not force:
                # Check for error only in case no previous error happened
                check_error(error_queue)

                
if __name__ == '__main__':
    t0 = datetime.datetime.now()
    
    LOG_FILE = open('out2pdf-main.log', 'w')
    
    try:
        tex.preinstall_packages()
    except tex.MikTexException as e:
        log_output(e.message)
        log_output('Stdout:\n')
        log_output(e.stdout)
        log_output('Stderr:\n')
        log_output(e.stderr)
        exit(1)
    
    proc_count = multiprocessing.cpu_count() * 2
    queue = multiprocessing.Queue(proc_count * 2)
    error_queue = multiprocessing.Queue(proc_count * 2)
    
    processes = [multiprocessing.Process(target=process, args=(i + 1, queue, error_queue))
                    for i in range(proc_count)]
    for p in processes:
        p.start()
    
    try:
        for ac_eng_folder in TASKS:
            task = ALL_TASKS[ac_eng_folder]
            ac_eng_folder = os.path.join(DATA_FOLDER, ac_eng_folder)
            ac_eng = task['ac_eng']
            for takeoff_or_landing in ('takeoff', 'landing'):
                grouped_folders = {}
                for case_folder in task[takeoff_or_landing]:
                    if TARGET_FOLDERS is not None and case_folder not in TARGET_FOLDERS:
                        continue
                    if case_folder in FOLDER_GROUP_RULES:
                        group = FOLDER_GROUP_RULES[case_folder]
                        grouped_folders.setdefault(group, [])
                        grouped_folders[group].append(case_folder)
                    else:
                        enqueue_and_check(queue, error_queue,
                            dict(ac_eng_folder=ac_eng_folder,
                                ac_eng=ac_eng,
                                type=takeoff_or_landing,
                                task=([case_folder], case_folder)))
                for group, folders in grouped_folders.iteritems():
                    enqueue_and_check(queue, error_queue,
                        dict(ac_eng_folder=ac_eng_folder,
                            ac_eng=ac_eng,
                            type=takeoff_or_landing,
                            task=(folders, group)))

        for _ in range(proc_count):
            enqueue_and_check(queue, error_queue, None)
        
        finalize(processes, error_queue)
    except KeyboardInterrupt:
        finalize(processes, error_queue, True)
    
    delta_time = datetime.datetime.now() - t0
    log_output("Total time taken: %s\n" % str(delta_time))
    
    LOG_FILE.close()
    
    if ERROR_PRESENT is True:
        import ctypes
        ctypes.windll.user32.MessageBoxA(0,
            "An error has occurred. Please check the log!",
            "BPS Utils",
            # MB_OK, MB_ICONERROR, MB_SYSTEMMODAL
            0x00000000L | 0x00000010 | 0x00001000)
        exit(1)
    
    