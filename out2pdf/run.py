
import os
import multiprocessing
import traceback
import sys
import datetime
import Queue
import codecs
import shutil

from task import *
from preprocess import preprocess
import tex

with open(AIRPORT_FILE, 'r') as f:
    APT_CODES = f.read().split()

PROC_ID = 0
LOG_FILE = None

def log_output(data):
    sys.stdout.write("(%d) %s" % (PROC_ID, data))
    LOG_FILE.write(data)


MOSCOW_APTS = ('UUDD', 'UUWW', 'UUEE')
    
def process_file(data_fname, is_takeoff, ac_eng, apt_code, pdf_folder, pdf_fname_template, temp_folder):
    
    pdf_basename = os.path.basename(pdf_fname_template % dict(ac_eng=ac_eng, code=apt_code))
    
    if apt_code in MOSCOW_APTS:
        pdf_basename = '_' + pdf_basename
    
    with open(data_fname, 'r') as f:
        data = [unicode(l, 'cp1251') for l in f.readlines()]
    
    data = preprocess(data, ac_eng, is_takeoff)
    tex_src = tex.make_xelatex_src(apt_code, data)
    
    tex_fname = os.path.join(temp_folder, pdf_basename[:-4] + '.tex')
    with open(tex_fname, 'w') as f:
        codecs.getwriter('utf-8')(f).writelines(tex_src)
    
    tex.compile_xelatex(tex_fname, pdf_folder, temp_folder)


def process_folder(ac_eng_folder, case_folder, ac_eng, is_takeoff):
    cwd = os.getcwd()
    os.chdir(ac_eng_folder)

    log_output("'%s' %s started.\n" % (ac_eng_folder, case_folder))
    t0 = datetime.datetime.now()

    try:
        pdf_folder = case_folder + '_PDF'
        temp_folder = case_folder + '_AUX'
        for f in [pdf_folder, temp_folder]:
            if not os.path.exists(f): os.makedirs(f)
        
        for apt_code in APT_CODES:
            data_fname = os.path.join(case_folder, apt_code + '.out')
            pdf_fname_template = PDF_NAME_TEMPLATES[case_folder]
            process_file(
                data_fname, is_takeoff,
                ac_eng, apt_code, pdf_folder,
                pdf_fname_template, temp_folder)

        shutil.rmtree(temp_folder)
    finally:
        os.chdir(cwd)
    
    delta_time = datetime.datetime.now() - t0
    log_output("'%s' %s finished. Time taken: %s.\n" % (ac_eng_folder, case_folder, str(delta_time)))
    
 
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
            process_folder(*args)

    except KeyboardInterrupt:
        log_output('Terminating.\n')
    except tex.MikTexException as e:
        log_output(e.message)
        log_output('Stdout:\n')
        log_output(e.stdout)
        log_output('Stderr:\n')
        log_output(e.stderr)
        log_output('Terminating.\n')
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
        

def check_error(error_queue):
    try:
        id = error_queue.get_nowait()
        log_output('Error in process %d.\n' % id)
        raise KeyboardInterrupt
    except Queue.Empty:
        pass
        
def enqueue_and_check(queue, error_queue, args):
    while True:
        try:
            queue.put(args, True, 1)
            break
        except Queue.Full:
            pass
        check_error(error_queue)

        
def finalize(processes, error_queue, force=False):
    if force:
        log_output('Finalizing...\n')
    else:
        log_output('Waiting for all to finish...\n')
    
    timeout = 2
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
            for case_folder in task['takeoff']:
                if TARGET_FOLDERS is None or case_folder in TARGET_FOLDERS:
                    enqueue_and_check(queue, error_queue, (ac_eng_folder, case_folder, ac_eng, True))
            for case_folder in task['landing']:
                if TARGET_FOLDERS is None or case_folder in TARGET_FOLDERS:
                    enqueue_and_check(queue, error_queue, (ac_eng_folder, case_folder, ac_eng, False))

        for _ in range(proc_count):
            enqueue_and_check(queue, error_queue, None)
        
        finalize(processes, error_queue)
    except KeyboardInterrupt:
        finalize(processes, error_queue, True)
    
    delta_time = datetime.datetime.now() - t0
    log_output("Total time taken: %s\n" % str(delta_time))
    
    LOG_FILE.close()