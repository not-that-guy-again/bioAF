profiles {
    bioaf_slurm {
        process.executor = 'slurm'
        process.queue = '${slurm_queue}'
        process.clusterOptions = '--account=${slurm_account}'
        singularity.enabled = true
        singularity.autoMounts = true
        singularity.cacheDir = '${container_cache}'
        params.outdir = '${results_dir}'
        workDir = '${work_dir}'
        timeline.enabled = true
        timeline.file = 'pipeline_info/timeline.html'
        report.enabled = true
        report.file = 'pipeline_info/report.html'
        trace.enabled = true
        trace.file = 'pipeline_info/trace.tsv'
        trace.fields = 'task_id,hash,native_id,process,tag,name,status,exit,submit,start,complete,duration,realtime,%cpu,peak_rss,peak_vmem,rchar,wchar'
    }
}
