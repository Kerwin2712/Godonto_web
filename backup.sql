--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: unaccent; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public;


--
-- Name: EXTENSION unaccent; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION unaccent IS 'text search dictionary that removes accents';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: access_keys; Type: TABLE; Schema: public; Owner: godonto_user1
--

CREATE TABLE public.access_keys (
    id integer NOT NULL,
    key character varying(50) NOT NULL,
    used boolean DEFAULT false NOT NULL,
    created_by integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.access_keys OWNER TO godonto_user1;

--
-- Name: access_keys_id_seq; Type: SEQUENCE; Schema: public; Owner: godonto_user1
--

CREATE SEQUENCE public.access_keys_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.access_keys_id_seq OWNER TO godonto_user1;

--
-- Name: access_keys_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: godonto_user1
--

ALTER SEQUENCE public.access_keys_id_seq OWNED BY public.access_keys.id;


--
-- Name: appointment_treatments; Type: TABLE; Schema: public; Owner: godonto_user1
--

CREATE TABLE public.appointment_treatments (
    appointment_id integer NOT NULL,
    treatment_id integer NOT NULL,
    price numeric(10,2) NOT NULL,
    notes text
);


ALTER TABLE public.appointment_treatments OWNER TO godonto_user1;

--
-- Name: appointments; Type: TABLE; Schema: public; Owner: godonto_user1
--

CREATE TABLE public.appointments (
    id integer NOT NULL,
    client_id integer NOT NULL,
    status character varying(20) DEFAULT 'scheduled'::character varying NOT NULL,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    date date,
    hour time without time zone
);


ALTER TABLE public.appointments OWNER TO godonto_user1;

--
-- Name: appointments_id_seq; Type: SEQUENCE; Schema: public; Owner: godonto_user1
--

CREATE SEQUENCE public.appointments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.appointments_id_seq OWNER TO godonto_user1;

--
-- Name: appointments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: godonto_user1
--

ALTER SEQUENCE public.appointments_id_seq OWNED BY public.appointments.id;


--
-- Name: clients; Type: TABLE; Schema: public; Owner: godonto_user1
--

CREATE TABLE public.clients (
    id integer NOT NULL,
    user_id integer,
    name character varying(100) NOT NULL,
    cedula character varying(20) NOT NULL,
    phone character varying(20),
    birth_date date,
    address text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    email character varying(255)
);


ALTER TABLE public.clients OWNER TO godonto_user1;

--
-- Name: clients_id_seq; Type: SEQUENCE; Schema: public; Owner: godonto_user1
--

CREATE SEQUENCE public.clients_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clients_id_seq OWNER TO godonto_user1;

--
-- Name: clients_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: godonto_user1
--

ALTER SEQUENCE public.clients_id_seq OWNED BY public.clients.id;


--
-- Name: debt_payments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.debt_payments (
    id integer NOT NULL,
    payment_id integer NOT NULL,
    debt_id integer NOT NULL,
    amount_applied numeric(10,2) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.debt_payments OWNER TO postgres;

--
-- Name: debt_payments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.debt_payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.debt_payments_id_seq OWNER TO postgres;

--
-- Name: debt_payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.debt_payments_id_seq OWNED BY public.debt_payments.id;


--
-- Name: debts; Type: TABLE; Schema: public; Owner: godonto_user1
--

CREATE TABLE public.debts (
    id integer NOT NULL,
    client_id integer NOT NULL,
    amount numeric(10,2) NOT NULL,
    description text,
    due_date date,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    paid_amount numeric(10,2) DEFAULT 0,
    paid_at timestamp without time zone,
    CONSTRAINT debts_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'paid'::character varying, 'canceled'::character varying])::text[])))
);


ALTER TABLE public.debts OWNER TO godonto_user1;

--
-- Name: debts_id_seq; Type: SEQUENCE; Schema: public; Owner: godonto_user1
--

CREATE SEQUENCE public.debts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.debts_id_seq OWNER TO godonto_user1;

--
-- Name: debts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: godonto_user1
--

ALTER SEQUENCE public.debts_id_seq OWNED BY public.debts.id;


--
-- Name: dentists; Type: TABLE; Schema: public; Owner: godonto_user1
--

CREATE TABLE public.dentists (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    specialty character varying(100),
    phone character varying(20),
    email character varying(100),
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.dentists OWNER TO godonto_user1;

--
-- Name: dentists_id_seq; Type: SEQUENCE; Schema: public; Owner: godonto_user1
--

CREATE SEQUENCE public.dentists_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dentists_id_seq OWNER TO godonto_user1;

--
-- Name: dentists_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: godonto_user1
--

ALTER SEQUENCE public.dentists_id_seq OWNED BY public.dentists.id;


--
-- Name: medical_history; Type: TABLE; Schema: public; Owner: godonto_user1
--

CREATE TABLE public.medical_history (
    id integer NOT NULL,
    client_id integer NOT NULL,
    record_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    description text NOT NULL,
    treatment_details text,
    notes text,
    created_by integer
);


ALTER TABLE public.medical_history OWNER TO godonto_user1;

--
-- Name: medical_history_id_seq; Type: SEQUENCE; Schema: public; Owner: godonto_user1
--

CREATE SEQUENCE public.medical_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.medical_history_id_seq OWNER TO godonto_user1;

--
-- Name: medical_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: godonto_user1
--

ALTER SEQUENCE public.medical_history_id_seq OWNED BY public.medical_history.id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: godonto_user1
--

CREATE TABLE public.payments (
    id integer NOT NULL,
    client_id integer NOT NULL,
    appointment_id integer,
    amount numeric(10,2) NOT NULL,
    payment_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    method character varying(50) NOT NULL,
    status character varying(20) DEFAULT 'completed'::character varying NOT NULL,
    invoice_number character varying(50),
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by integer,
    CONSTRAINT payments_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'completed'::character varying, 'failed'::character varying, 'refunded'::character varying])::text[])))
);


ALTER TABLE public.payments OWNER TO godonto_user1;

--
-- Name: payments_id_seq; Type: SEQUENCE; Schema: public; Owner: godonto_user1
--

CREATE SEQUENCE public.payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payments_id_seq OWNER TO godonto_user1;

--
-- Name: payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: godonto_user1
--

ALTER SEQUENCE public.payments_id_seq OWNED BY public.payments.id;


--
-- Name: treatments; Type: TABLE; Schema: public; Owner: godonto_user1
--

CREATE TABLE public.treatments (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    price numeric(10,2) NOT NULL,
    duration interval NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.treatments OWNER TO godonto_user1;

--
-- Name: treatments_id_seq; Type: SEQUENCE; Schema: public; Owner: godonto_user1
--

CREATE SEQUENCE public.treatments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.treatments_id_seq OWNER TO godonto_user1;

--
-- Name: treatments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: godonto_user1
--

ALTER SEQUENCE public.treatments_id_seq OWNED BY public.treatments.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: godonto_user1
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    password_hash character varying(255) NOT NULL,
    email character varying(100) NOT NULL,
    is_admin boolean DEFAULT false NOT NULL,
    is_verified boolean DEFAULT false NOT NULL,
    verification_code character varying(6),
    verification_expires timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_active boolean
);


ALTER TABLE public.users OWNER TO godonto_user1;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: godonto_user1
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO godonto_user1;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: godonto_user1
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: access_keys id; Type: DEFAULT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.access_keys ALTER COLUMN id SET DEFAULT nextval('public.access_keys_id_seq'::regclass);


--
-- Name: appointments id; Type: DEFAULT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.appointments ALTER COLUMN id SET DEFAULT nextval('public.appointments_id_seq'::regclass);


--
-- Name: clients id; Type: DEFAULT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.clients ALTER COLUMN id SET DEFAULT nextval('public.clients_id_seq'::regclass);


--
-- Name: debt_payments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.debt_payments ALTER COLUMN id SET DEFAULT nextval('public.debt_payments_id_seq'::regclass);


--
-- Name: debts id; Type: DEFAULT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.debts ALTER COLUMN id SET DEFAULT nextval('public.debts_id_seq'::regclass);


--
-- Name: dentists id; Type: DEFAULT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.dentists ALTER COLUMN id SET DEFAULT nextval('public.dentists_id_seq'::regclass);


--
-- Name: medical_history id; Type: DEFAULT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.medical_history ALTER COLUMN id SET DEFAULT nextval('public.medical_history_id_seq'::regclass);


--
-- Name: payments id; Type: DEFAULT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.payments ALTER COLUMN id SET DEFAULT nextval('public.payments_id_seq'::regclass);


--
-- Name: treatments id; Type: DEFAULT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.treatments ALTER COLUMN id SET DEFAULT nextval('public.treatments_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: access_keys; Type: TABLE DATA; Schema: public; Owner: godonto_user1
--

COPY public.access_keys (id, key, used, created_by, created_at) FROM stdin;
\.


--
-- Data for Name: appointment_treatments; Type: TABLE DATA; Schema: public; Owner: godonto_user1
--

COPY public.appointment_treatments (appointment_id, treatment_id, price, notes) FROM stdin;
\.


--
-- Data for Name: appointments; Type: TABLE DATA; Schema: public; Owner: godonto_user1
--

COPY public.appointments (id, client_id, status, notes, created_at, updated_at, date, hour) FROM stdin;
\.


--
-- Data for Name: clients; Type: TABLE DATA; Schema: public; Owner: godonto_user1
--

COPY public.clients (id, user_id, name, cedula, phone, birth_date, address, created_at, updated_at, email) FROM stdin;
\.


--
-- Data for Name: debt_payments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.debt_payments (id, payment_id, debt_id, amount_applied, created_at) FROM stdin;
\.


--
-- Data for Name: debts; Type: TABLE DATA; Schema: public; Owner: godonto_user1
--

COPY public.debts (id, client_id, amount, description, due_date, status, created_at, updated_at, paid_amount, paid_at) FROM stdin;
\.


--
-- Data for Name: dentists; Type: TABLE DATA; Schema: public; Owner: godonto_user1
--

COPY public.dentists (id, name, specialty, phone, email, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: medical_history; Type: TABLE DATA; Schema: public; Owner: godonto_user1
--

COPY public.medical_history (id, client_id, record_date, description, treatment_details, notes, created_by) FROM stdin;
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: godonto_user1
--

COPY public.payments (id, client_id, appointment_id, amount, payment_date, method, status, invoice_number, notes, created_at, created_by) FROM stdin;
\.


--
-- Data for Name: treatments; Type: TABLE DATA; Schema: public; Owner: godonto_user1
--

COPY public.treatments (id, name, description, price, duration, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: godonto_user1
--

COPY public.users (id, username, password_hash, email, is_admin, is_verified, verification_code, verification_expires, created_at, updated_at, is_active) FROM stdin;
2	27934140	$2b$12$H/JfG828z0JdGY0Gm3bxA.Zx01JNUcL35RM37de2exKI6Q.m/s5RW	admin	t	t	\N	\N	2025-05-01 14:02:32.311681	2025-05-01 14:02:32.311681	\N
\.


--
-- Name: access_keys_id_seq; Type: SEQUENCE SET; Schema: public; Owner: godonto_user1
--

SELECT pg_catalog.setval('public.access_keys_id_seq', 1, false);


--
-- Name: appointments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: godonto_user1
--

SELECT pg_catalog.setval('public.appointments_id_seq', 11, true);


--
-- Name: clients_id_seq; Type: SEQUENCE SET; Schema: public; Owner: godonto_user1
--

SELECT pg_catalog.setval('public.clients_id_seq', 3, true);


--
-- Name: debt_payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.debt_payments_id_seq', 1, false);


--
-- Name: debts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: godonto_user1
--

SELECT pg_catalog.setval('public.debts_id_seq', 3, true);


--
-- Name: dentists_id_seq; Type: SEQUENCE SET; Schema: public; Owner: godonto_user1
--

SELECT pg_catalog.setval('public.dentists_id_seq', 1, false);


--
-- Name: medical_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: godonto_user1
--

SELECT pg_catalog.setval('public.medical_history_id_seq', 1, false);


--
-- Name: payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: godonto_user1
--

SELECT pg_catalog.setval('public.payments_id_seq', 9, true);


--
-- Name: treatments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: godonto_user1
--

SELECT pg_catalog.setval('public.treatments_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: godonto_user1
--

SELECT pg_catalog.setval('public.users_id_seq', 2, true);


--
-- Name: access_keys access_keys_key_key; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.access_keys
    ADD CONSTRAINT access_keys_key_key UNIQUE (key);


--
-- Name: access_keys access_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.access_keys
    ADD CONSTRAINT access_keys_pkey PRIMARY KEY (id);


--
-- Name: appointment_treatments appointment_treatments_pkey; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.appointment_treatments
    ADD CONSTRAINT appointment_treatments_pkey PRIMARY KEY (appointment_id, treatment_id);


--
-- Name: appointments appointments_pkey; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT appointments_pkey PRIMARY KEY (id);


--
-- Name: clients clients_cedula_key; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_cedula_key UNIQUE (cedula);


--
-- Name: clients clients_pkey; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_pkey PRIMARY KEY (id);


--
-- Name: clients clients_user_id_key; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_user_id_key UNIQUE (user_id);


--
-- Name: debt_payments debt_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.debt_payments
    ADD CONSTRAINT debt_payments_pkey PRIMARY KEY (id);


--
-- Name: debts debts_pkey; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.debts
    ADD CONSTRAINT debts_pkey PRIMARY KEY (id);


--
-- Name: dentists dentists_pkey; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.dentists
    ADD CONSTRAINT dentists_pkey PRIMARY KEY (id);


--
-- Name: medical_history medical_history_pkey; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.medical_history
    ADD CONSTRAINT medical_history_pkey PRIMARY KEY (id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: treatments treatments_pkey; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.treatments
    ADD CONSTRAINT treatments_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: idx_appointments_client; Type: INDEX; Schema: public; Owner: godonto_user1
--

CREATE INDEX idx_appointments_client ON public.appointments USING btree (client_id);


--
-- Name: idx_clients_cedula; Type: INDEX; Schema: public; Owner: godonto_user1
--

CREATE INDEX idx_clients_cedula ON public.clients USING btree (cedula);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: godonto_user1
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: access_keys access_keys_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.access_keys
    ADD CONSTRAINT access_keys_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: appointment_treatments appointment_treatments_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.appointment_treatments
    ADD CONSTRAINT appointment_treatments_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.appointments(id) ON DELETE CASCADE;


--
-- Name: appointment_treatments appointment_treatments_treatment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.appointment_treatments
    ADD CONSTRAINT appointment_treatments_treatment_id_fkey FOREIGN KEY (treatment_id) REFERENCES public.treatments(id);


--
-- Name: appointments appointments_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT appointments_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id) ON DELETE CASCADE;


--
-- Name: clients clients_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: debt_payments debt_payments_debt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.debt_payments
    ADD CONSTRAINT debt_payments_debt_id_fkey FOREIGN KEY (debt_id) REFERENCES public.debts(id) ON DELETE CASCADE;


--
-- Name: debt_payments debt_payments_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.debt_payments
    ADD CONSTRAINT debt_payments_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id) ON DELETE CASCADE;


--
-- Name: debts debts_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.debts
    ADD CONSTRAINT debts_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id) ON DELETE CASCADE;


--
-- Name: medical_history medical_history_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.medical_history
    ADD CONSTRAINT medical_history_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id) ON DELETE CASCADE;


--
-- Name: medical_history medical_history_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.medical_history
    ADD CONSTRAINT medical_history_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: payments payments_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.appointments(id);


--
-- Name: payments payments_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id) ON DELETE CASCADE;


--
-- Name: payments payments_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: godonto_user1
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

