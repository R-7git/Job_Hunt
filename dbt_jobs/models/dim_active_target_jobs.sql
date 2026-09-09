select 
    job_id,
    title,
    company,
    location,
    url,
    fit_score,
    match_reason,
    scouted_at
from {{ ref('stg_jobs') }}
