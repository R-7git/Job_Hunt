{% set role = var('target_role') %}
{% set exp = var('experience_level') %}
{% set remote = var('remote_only') %}

with raw_data as (
    select * from jobs
)

select
    id as job_id,
    title,
    company,
    location,
    url,
    source,
    summary,
    fit_score,
    match_reason,
    status,
    scouted_at,
    '{{ role }}' as active_target_role,
    datetime('now') as transformed_at
from raw_data
where 1=1

    -- 1. Target Role Keywords
    {% if role == 'Data Engineering' %}
        and (
            lower(title) like '%data engineer%' 
            or lower(title) like '%sql%' 
            or lower(title) like '%snowflake%' 
            or lower(title) like '%etl%' 
            or lower(title) like '%pipeline%'
            or lower(title) like '%database%'
            or lower(title) like '%data warehouse%'
        )
    {% endif %}

    -- 2. Experience Exclusion Logic (Block Senior Roles, Allow Standard/Fresher Roles)
    {% if exp == 'Fresher' %}
        and lower(title) not like '%senior%'
        and lower(title) not like '%sr.%'
        and lower(title) not like '%sr %'
        and lower(title) not like '%principal%'
        and lower(title) not like '%lead%'
        and lower(title) not like '%staff%'
        and lower(title) not like '%manager%'
        and lower(title) not like '%director%'
        and lower(title) not like '%vp %'
        and lower(title) not like '%head of%'
    {% endif %}

    -- 3. Remote Logic
    {% if remote %}
        and (
            lower(location) like '%remote%' 
            or lower(title) like '%remote%' 
            or lower(summary) like '%work from home%'
            or lower(summary) like '%fully remote%'
            or lower(summary) like '%100% remote%'
        )
    {% endif %}
