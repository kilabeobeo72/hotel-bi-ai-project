-- File: lab_project/dbt/hotel_dw/models/marts/dim_channel.sql
{{ config(
    materialized='table',
    schema='dds'
) }}

WITH distinct_channels AS (
    SELECT DISTINCT
        market_segment,
        distribution_channel,
        COALESCE(agent_code, 'No Agent') AS agent_code,
        COALESCE(company_code, 'No Company') AS company_code
    FROM {{ ref('stg_hotel_bookings') }}
)

SELECT
    MD5(
        CONCAT_WS(
            '|',
            market_segment,
            distribution_channel,
            agent_code,
            company_code
        )
    ) AS channel_key,
    market_segment,
    distribution_channel,
    agent_code,
    company_code
FROM distinct_channels