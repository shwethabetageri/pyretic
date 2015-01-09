import time
import os
from functools import wraps

stats = {}
classifier = {}
general_stats = {}
monitoring = False

path = '/home/mininet/pyretic/pyretic/evaluations/results/'
dfa_path = '/tmp/pyretic-regexes.txt.dot'
symbol_path = '/tmp/symbols.txt'
pickle_path = '/tmp/pickle_symbols.txt'
rule_cnt_file = 'rule-count.txt'
clean_tmp = False


policies = []
pol_cls = []

# opt_flags
disjoint_enabled = False
integrate_enabled = False
multitable_enabled = False
ragel_enabled = False


def start(results_folder=None, opt_flags = None):
    global path
    global monitoring
    global dfa_path
    global symbol_path
    global clean_tmp

    global disjoint_enabled
    global integrate_enabled
    global multitable_enabled
    global ragel_enabled

    if results_folder:
        path = results_folder

    if opt_flags:
        (disjoint_enabled, integrate_enabled, multitable_enabled, ragel_enabled) = opt_flags

    if not os.path.exists(results_folder):
        os.mkdir(results_folder)

    clean_tmp = True
    try:
        os.remove(dfa_path)
        os.remove(symbol_path)
    except:
        clean_tmp = False

    monitoring = True

def stop():
    global monitoring
    global path
    global dfa_path
    global symbol_path
    global rule_cnt_file

    global ragel_enabled

    if monitoring:
        report_dfa(dfa_path, symbol_path, path, ragel_enabled)
        create_overall_report(path, rule_cnt_file, os.path.basename(dfa_path))
        create_excel_report(path, rule_cnt_file, os.path.basename(dfa_path))

    monitoring = False
def report_dfa(dfa_path, symbol_path, results_path, ragel_enabled):
    global clean_tmp
    if clean_tmp:
        import shutil
        try:
            if not ragel_enabled:
                shutil.copy(dfa_path, results_path)
            shutil.copy(symbol_path, results_path)
            shutil.copy(pickle_path, results_path)
        except:
            print 'exception in dfa report'


def create_overall_report(results_path, rule_cnt, dfa_path):
    def adjust_func(file_path):
        return os.path.join(results_path, file_path)


    f = open(adjust_func('performance_report.txt'), 'w')

    # rule count on switches
    try:
        g = open(adjust_func(rule_cnt), 'r');
        for line in g.readlines():
            f.write(line)
        g.close()
    except:
        pass

    # general statstics gathered
    try:
        g = open(adjust_func('general_stats.txt'), 'r')
        for line in g.readlines():
            f.write(line)
        f.write('--------------------------------------\n')
        g.close()
    except:
        pass

    # compile times
    def getFileName(file_name):
        return os.path.splitext(file_name)[0]

    files = os.listdir(results_path)
    profiles = [ p for p in files if (".profile" in p)]
    cls = [p for p in files if ".cls" in p]

    for prof in profiles:
        g = open(adjust_func(prof), 'r')
        name = prof[:-8]
        f.write(name + '\n')
        for line in g.readlines():
            f.write(line)
        g.close()
        c = [p for p in cls if getFileName(name) == getFileName(p)]
        if len(c) == 1:
            g = open(adjust_func(c[0]), 'r')
            for line in g.readlines():
                f.write(line)
        f.write('--------------------------------------\n')

    f.close()

def create_excel_report(results_path, rule_cnt, dfa_path):
    global multitable_enabled
    global integrate_enabled

    row = None
    if multitable_enabled:
        if integrate_enabled:
            row =  ["makeDFA_vector", 'compile', 'forwarding_compile', 
                    'in_table_compile', 'out_table_compile']
            row.extend(['tab'] * 13)


        else:
            row =  ["makeDFA_vector", 'compile', 'forwarding_compile', 
                    'tagging_compile', 'out_tagging_compile', 
                    'capture_compile', 'out_capture_compile', 
                    'in_table_compile', 'tab', 'out_table_compile', 'tab']
            row.extend(['tab'] * 13)

    else:
        row = ["makeDFA_vector", 'compile', 'forwarding_compile', 
                'tagging_compile', 'out_tagging_compile', 'tag_fwd_compile',
                'capture_compile', 'out_capture_compile', 'full_out_capture_compile']            
        row.extend(['tab'] * 13)
   
    create_excel_report_general(results_path, rule_cnt, dfa_path, row)

def gather_general_stats(stat_name, stat_value, init, aggr=True):
    global general_stats
    global path
    global monitoring

    if monitoring:
        if not aggr:
            general_stats[stat_name] = stat_value

        else:
            if not stat_name in general_stats:
                general_stats[stat_name] = init
            general_stats[stat_name] += stat_value
        f = open(os.path.join(path, 'general_stats.txt'), 'w')
        for s in general_stats:
            f.write('%s: %s\n' % (s, str(general_stats[s])))

        f.close()


def classifier_size(func):
    global classifier
    global path
    global monitoring

    @wraps(func)
    def profiled_func(*args, **kwargs):
        res = func(*args, **kwargs)

        if monitoring and res:
            fname = func.__name__

            if fname not in classifier:
                classifier[fname] = 0

            classifier[fname] = len(res.rules)

            f = open(os.path.join(path, '%s.cls' % fname), 'a')
            f.write(('classifier size: %d' % classifier[fname]) + '\n')
            f.write('print : %s \n' % str(res))
            f.write('---------------------------------\n')
            f.close()
        return res

    return profiled_func

def elapsed_time(func):
    global stats
    global path
    global monitoring

    @wraps(func)
    def profiled_func(*args, **kwargs):
        start_time = time.time()
        res = func(*args, **kwargs)

        if monitoring:
            elapsed = time.time() - start_time
            fname = func.__name__
            if fname not in stats:
                stats[fname] = [0, []] #ncalls, times
            stats[fname][0] += 1
            stats[fname][1].append(elapsed)

            f = open(os.path.join(path, '%s.profile' % fname), 'w')
            f.write(('number of calls: %d' % stats[fname][0]) + '\n')

            time_list = stats[fname][1]
            f.write( ('total time: %f' % sum(time_list)) + '\n')
            f.write( ('average time: %f' % ( sum(time_list) / len(time_list) )) + '\n')
            f.write('---times----\n')
            f.write(str(time_list) + '\n')

            f.close()


        return res

    return profiled_func

import yappi

def aggregate(func, stats):
    fname = "%s.profile" % (func.__name__)
    stats.sort('tavg')
    stats.print_all()
    try:
        stats.add(fname)
    except IOError:
        pass
    stats.save(fname)

################################################################################
##                     Older Table Types                                      ##
################################################################################
def create_excel_report_general(results_path, rule_cnt, dfa_path, row):
    def adjust_func(file_path):
        return os.path.join(results_path, file_path)

    f = open(adjust_func('excel_report.txt'), 'w')

    for c in row:
        if c == 'tab':
            f.write('0\t')
            continue
        cpath = adjust_func(c + '.profile')
        if os.path.exists(cpath):
            g = open(cpath, 'r')
            for line in g.readlines():
                if "average" in line:
                    f.write(line[line.index(':') + 2 :-1] + "\t")
                    break
            g.close()

            cpath = adjust_func(c + '.cls')
            if os.path.exists(cpath):
                g = open(cpath, 'r')
                cls = '\t'
                for line in g.readlines():
                    if "classifier size" in line:
                        cls = line[line.index(':') + 2 :-1] + "\t"
                f.write(cls)
                g.close()


        else:
            f.write('0\t0\t')

            #    f.write('\n')

    dfa_state_cnt = 0
    in_tagging_edge = 0
    out_tagging_edge = 0
    in_capture_edge = 0
    out_capture_edge = 0
    switch_cnt = 0
    rule_cnt = 0

    try:
        g = open(adjust_func('general_stats.txt'), 'r')
        for line in g.readlines():
            if "in tagging edges" in line:
                in_tagging_edge = int(line[line.index(':') + 2:-1])

            elif "out tagging edges" in line:
                out_tagging_edge = int(line[line.index(':') + 2:-1])

            elif 'in capture edges' in line:
                in_capture_edge = int(line[line.index(':') + 2 : -1])

            elif 'out capture edges' in line:
                out_capture_edge = int(line[line.index(':') + 2 : -1])

            elif 'switch count' in line:
                switch_cnt = int(line[line.index(':') + 2 :-1])

            elif 'rule count' in line:
                rule_cnt = int(line[line.index(':') + 2 : -1])
            
            elif 'dfa state count' in line:
                dfa_state_cnt = int(line[line.index(':') + 2 : -1])


        g.close()
    except:
        pass

    rule_avg = 0
    if switch_cnt and rule_cnt:
        rule_avg = float(rule_cnt) / switch_cnt

    gen_list = [rule_avg, rule_cnt, dfa_state_cnt, in_tagging_edge, out_tagging_edge, in_capture_edge, out_capture_edge]

    for gen in gen_list:
        f.write(str(gen) + "\t")
    f.write('\n')

    f.close()


def create_excel_report_inout_single_table(results_path, rule_cnt, dfa_path):
    cols = [ ["makeDFA_vector", 'compile', 'forwarding_compile', 
                'tagging_compile', 'out_tagging_compile', 'tag_fwd_compile',
                'capture_compile', 'out_capture_compile', 'full_out_capture_compile'],
                #['vf_tag_compile', 'vf_untag_compile', 'whole_policy_compile'],
            ]

    def adjust_func(file_path):
        return os.path.join(results_path, file_path)

    f = open(adjust_func('excel_report.txt'), 'w')

    for col in cols:
        for c in col:
            cpath = adjust_func(c + '.profile')
            if os.path.exists(cpath):
                g = open(cpath, 'r')
                for line in g.readlines():
                    if "average" in line:
                        f.write(line[line.index(':') + 2 :-1] + "\t")
                        break
                g.close()
            else:
                f.write('0\t')

            cpath = adjust_func(c + '.cls')
            if os.path.exists(cpath):
                g = open(cpath, 'r')
                cls = '\t'
                for line in g.readlines():
                    if "classifier size" in line:
                        cls = line[line.index(':') + 2 :-1] + "\t"
                f.write(cls)
                g.close()

        f.write('\n')

    dfa_state_cnt = 0
    try:
        g = open(adjust_func(dfa_path), 'r')
        for line in g.readlines():
            if 'shape' in line:
                dfa_state_cnt += 1

        g.close()
    except:
        pass


    in_tagging_edge = 0
    out_tagging_edge = 0
    in_capture_edge = 0
    out_capture_edge = 0
    switch_cnt = 0
    rule_cnt = 0

    try:
        g = open(adjust_func('general_stats.txt'), 'r')
        for line in g.readlines():
            if "in tagging edges" in line:
                in_tagging_edge = int(line[line.index(':') + 2:-1])

            elif "out tagging edges" in line:
                out_tagging_edge = int(line[line.index(':') + 2:-1])

            elif 'in capture edges' in line:
                in_capture_edge = int(line[line.index(':') + 2 : -1])

            elif 'out capture edges' in line:
                out_capture_edge = int(line[line.index(':') + 2 : -1])

            elif 'switch count' in line:
                switch_cnt = int(line[line.index(':') + 2 :-1])

            elif 'rule count' in line:
                rule_cnt = int(line[line.index(':') + 2 : -1])

        g.close()
    except:
        pass

    rule_avg = 0
    if switch_cnt and rule_cnt:
        rule_avg = float(rule_cnt) / switch_cnt

    gen_list = [rule_avg, rule_cnt, dfa_state_cnt, in_tagging_edge, out_tagging_edge, in_capture_edge, out_capture_edge]

    for gen in gen_list:
        f.write(str(gen) + "\t")
    f.write('\n')

    f.close()


def create_excel_report_simple(results_path, rule_cnt, dfa_path):
    cols = [ ["makeDFA_vector", 'compile', 'forwarding_compile', 'tagging_compile', 'capture_compile', 'tag_fw_cap_compile'],
                ['vf_tag_compile', 'vf_untag_compile', 'whole_policy_compile'],
            ]

    def adjust_func(file_path):
        return os.path.join(results_path, file_path)

    f = open(adjust_func('excel_report.txt'), 'w')

    for col in cols:
        for c in col:
            cpath = adjust_func(c + '.profile')
            if os.path.exists(cpath):
                g = open(cpath, 'r')
                for line in g.readlines():
                    if "average" in line:
                        f.write(line[line.index(':') + 2 :-1] + "\t")
                        break
                g.close()
            else:
                f.write('0\t')

            cpath = adjust_func(c + '.cls')
            if os.path.exists(cpath):
                g = open(cpath, 'r')
                for line in g.readlines():
                    cls = "\t"
                    if "classifier" in line:
                        cls = line[line.index(':') + 2 :-1] + "\t"

                f.write(cls)
                g.close()

        f.write('\n')

    dfa_state_cnt = 0
    try:
        g = open(adjust_func(dfa_path), 'r')
        for line in g.readlines():
            if 'shape' in line:
                dfa_state_cnt += 1

        g.close()
    except:
        pass


    '''rule_cnt = 0
    rule_avg = 0
   
    try:
        g = open(adjust_func(rule_cnt), 'r')
        for line in g.readlines():

            if 'total rule count' in line:
                rule_cnt = int(line[line.index(':') + 2 : -1])

            elif 'average rule count' in line:
                rule_avg = float(line[line.index(':') + 2 : -1])
        g.close()
    except:
        pass'''

    tagging_edge = 0
    capture_edge = 0
    switch_cnt = 0
    rule_cnt = 0

    try:
        g = open(adjust_func('general_stats.txt'), 'r')
        for line in g.readlines():
            if "tagging edges" in line:
                tagging_edge = int(line[line.index(':') + 2:-1])

            elif 'capture edges' in line:
                capture_edge = int(line[line.index(':') + 2 : -1])

            elif 'switch count' in line:
                switch_cnt = int(line[line.index(':') + 2 :-1])

            elif 'rule count' in line:
                rule_cnt = int(line[line.index(':') + 2 : -1])

        g.close()
    except:
        pass

    rule_avg = 0
    if switch_cnt and rule_cnt:
        rule_avg = float(rule_cnt) / switch_cnt

    gen_list = [rule_avg, rule_cnt, dfa_state_cnt, tagging_edge, capture_edge]

    for gen in gen_list:
        f.write(str(gen) + "\t")
    f.write('\n')

    f.close()

