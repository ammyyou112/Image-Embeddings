-- Table: public.files

-- DROP TABLE IF EXISTS public.files;

DROP TABLE IF EXISTS public.files;
CREATE TABLE IF NOT EXISTS files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    path VARCHAR(255) NOT NULL,
    file_content BYTEA
);

ALTER TABLE IF EXISTS public.files
    OWNER to postgres;
