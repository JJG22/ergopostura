-- ErgoPostura: estructura completa de la base de datos (MySQL 8.4)
--
-- Incluye las 26 tablas: las del sistema y las internas de Django (auth_*, django_*).
-- Generado con mysqldump a partir de la base real. Solo crea la estructura, sin datos.
-- Ejecútelo en una base vacía; no borra nada, y falla si las tablas ya existen.

CREATE DATABASE IF NOT EXISTS ergopostura CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE ergopostura;

SET FOREIGN_KEY_CHECKS = 0;

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `email` varchar(254) NOT NULL,
  `role` varchar(20) NOT NULL,
  `company_id` bigint DEFAULT NULL,
  `must_change_password` tinyint(1) NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `accounts_user_company_id_bc91fe74_fk_companies_company_id` (`company_id`),
  KEY `accounts_user_created_by_id_ba68b522_fk_accounts_user_id` (`created_by_id`),
  CONSTRAINT `accounts_user_company_id_bc91fe74_fk_companies_company_id` FOREIGN KEY (`company_id`) REFERENCES `companies_company` (`id`),
  CONSTRAINT `accounts_user_created_by_id_ba68b522_fk_accounts_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `user_company_only_for_company_role` CHECK ((((`company_id` is not null) and (`role` = _utf8mb4'empresa')) or ((`role` <> _utf8mb4'empresa') and (`company_id` is null)))),
  CONSTRAINT `user_role_valid` CHECK ((`role` in (_utf8mb4'admin',_utf8mb4'ingeniero',_utf8mb4'empresa')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_user_groups_user_id_group_id_59c0b32f_uniq` (`user_id`,`group_id`),
  KEY `accounts_user_groups_group_id_bd11a704_fk_auth_group_id` (`group_id`),
  CONSTRAINT `accounts_user_groups_group_id_bd11a704_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `accounts_user_groups_user_id_52b62117_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_user_user_permi_user_id_permission_id_2ab516c2_uniq` (`user_id`,`permission_id`),
  KEY `accounts_user_user_p_permission_id_113bb443_fk_auth_perm` (`permission_id`),
  CONSTRAINT `accounts_user_user_p_permission_id_113bb443_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `accounts_user_user_p_user_id_e4f0a161_fk_accounts_` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `companies_area` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `name` varchar(150) NOT NULL,
  `description` longtext NOT NULL,
  `site_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `area_unique_name_in_site` (`site_id`,(lower(`name`))),
  CONSTRAINT `companies_area_site_id_3b36850f_fk_companies_site_id` FOREIGN KEY (`site_id`) REFERENCES `companies_site` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `companies_company` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `name` varchar(200) NOT NULL,
  `nit` varchar(10) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `municipality_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nit` (`nit`),
  KEY `companies_company_municipality_id_71991e81_fk_geography` (`municipality_id`),
  CONSTRAINT `companies_company_municipality_id_71991e81_fk_geography` FOREIGN KEY (`municipality_id`) REFERENCES `geography_municipality` (`id`),
  CONSTRAINT `company_nit_format` CHECK (regexp_like(`nit`,_utf8mb4'^[1-9][0-9]{5,9}$',_utf8mb4'c'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `companies_position` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `name` varchar(150) NOT NULL,
  `description` longtext NOT NULL,
  `area_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `position_unique_name_in_area` (`area_id`,(lower(`name`))),
  CONSTRAINT `companies_position_area_id_d59276d9_fk_companies_area_id` FOREIGN KEY (`area_id`) REFERENCES `companies_area` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `companies_site` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `name` varchar(150) NOT NULL,
  `address` varchar(200) NOT NULL,
  `company_id` bigint NOT NULL,
  `municipality_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `site_unique_name_in_company` (`company_id`,(lower(`name`))),
  KEY `companies_site_municipality_id_1575d142_fk_geography` (`municipality_id`),
  CONSTRAINT `companies_site_company_id_bfe6c00a_fk_companies_company_id` FOREIGN KEY (`company_id`) REFERENCES `companies_company` (`id`),
  CONSTRAINT `companies_site_municipality_id_1575d142_fk_geography` FOREIGN KEY (`municipality_id`) REFERENCES `geography_municipality` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `companies_worker` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `first_name` varchar(120) NOT NULL,
  `last_name` varchar(120) NOT NULL,
  `document_type` varchar(3) NOT NULL,
  `document_number` varchar(20) NOT NULL,
  `hired_on` date DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `position_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `worker_unique_document_in_position` (`position_id`,`document_type`,`document_number`),
  CONSTRAINT `companies_worker_position_id_308bb7a4_fk_companies_position_id` FOREIGN KEY (`position_id`) REFERENCES `companies_position` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `contracts_contract` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `code` varchar(50) NOT NULL,
  `kind` varchar(30) NOT NULL,
  `service` longtext NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `value` decimal(14,0) DEFAULT NULL,
  `responsible_name` varchar(150) NOT NULL,
  `responsible_role` varchar(120) NOT NULL,
  `responsible_email` varchar(254) NOT NULL,
  `responsible_phone` varchar(30) NOT NULL,
  `notes` longtext NOT NULL,
  `file_data` longblob NOT NULL,
  `file_name` varchar(255) NOT NULL,
  `file_size` int unsigned NOT NULL,
  `file_sha256` varchar(64) NOT NULL,
  `ai_summary` json NOT NULL,
  `ai_model` varchar(60) NOT NULL,
  `ai_generated_at` datetime(6) DEFAULT NULL,
  `company_id` bigint NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `contracts_contract_company_id_b071885c_fk_companies_company_id` (`company_id`),
  KEY `contracts_contract_created_by_id_1552fda4_fk_accounts_user_id` (`created_by_id`),
  CONSTRAINT `contracts_contract_company_id_b071885c_fk_companies_company_id` FOREIGN KEY (`company_id`) REFERENCES `companies_company` (`id`),
  CONSTRAINT `contracts_contract_created_by_id_1552fda4_fk_accounts_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `contract_dates_in_order` CHECK ((`end_date` >= `start_date`)),
  CONSTRAINT `contracts_contract_chk_1` CHECK ((`file_size` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `contracts_contractreading` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `sha256` varchar(64) NOT NULL,
  `summary` json NOT NULL,
  `model` varchar(60) NOT NULL,
  `requested_by_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `sha256` (`sha256`),
  KEY `contracts_contractre_requested_by_id_9baf30c5_fk_accounts_` (`requested_by_id`),
  CONSTRAINT `contracts_contractre_requested_by_id_9baf30c5_fk_accounts_` FOREIGN KEY (`requested_by_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `evaluations_evaluation` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `evaluated_on` date NOT NULL,
  `status` varchar(20) NOT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  `activity_description` longtext NOT NULL,
  `worker_context` longtext NOT NULL,
  `carries_load` tinyint(1) NOT NULL,
  `load_weight_kg` decimal(6,2) DEFAULT NULL,
  `repetitive_movements` tinyint(1) NOT NULL,
  `repetition_notes` varchar(250) NOT NULL,
  `evaluator_id` bigint NOT NULL,
  `position_id` bigint NOT NULL,
  `visit_id` bigint NOT NULL,
  `worker_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `evaluations_evaluation_evaluator_id_50207f4a_fk_accounts_user_id` (`evaluator_id`),
  KEY `evaluations_evaluati_position_id_1cdf5208_fk_companies` (`position_id`),
  KEY `evaluations_evaluation_visit_id_a6f33813_fk_visits_visit_id` (`visit_id`),
  KEY `evaluations_evaluation_worker_id_59baf8d2_fk_companies_worker_id` (`worker_id`),
  CONSTRAINT `evaluations_evaluati_position_id_1cdf5208_fk_companies` FOREIGN KEY (`position_id`) REFERENCES `companies_position` (`id`),
  CONSTRAINT `evaluations_evaluation_evaluator_id_50207f4a_fk_accounts_user_id` FOREIGN KEY (`evaluator_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `evaluations_evaluation_visit_id_a6f33813_fk_visits_visit_id` FOREIGN KEY (`visit_id`) REFERENCES `visits_visit` (`id`),
  CONSTRAINT `evaluations_evaluation_worker_id_59baf8d2_fk_companies_worker_id` FOREIGN KEY (`worker_id`) REFERENCES `companies_worker` (`id`),
  CONSTRAINT `evaluation_completed_has_date` CHECK (((`status` = _utf8mb4'borrador') or (`completed_at` is not null))),
  CONSTRAINT `evaluation_weight_requires_load` CHECK (((`load_weight_kg` is null) or ((`carries_load` = 0x01) and (`load_weight_kg` > 0))))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `evaluations_posture` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `name` varchar(150) NOT NULL,
  `side` varchar(10) NOT NULL,
  `duration_value` decimal(7,2) NOT NULL,
  `duration_unit` varchar(10) NOT NULL,
  `evaluation_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `posture_unique_name_side_in_evaluation` (`evaluation_id`,(lower(`name`)),`side`),
  CONSTRAINT `evaluations_posture_evaluation_id_e7908a6e_fk_evaluatio` FOREIGN KEY (`evaluation_id`) REFERENCES `evaluations_evaluation` (`id`),
  CONSTRAINT `posture_duration_positive` CHECK ((`duration_value` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `evaluations_posturephoto` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `data` longblob NOT NULL,
  `content_type` varchar(50) NOT NULL,
  `width` int unsigned NOT NULL,
  `height` int unsigned NOT NULL,
  `original_name` varchar(255) NOT NULL,
  `posture_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `evaluations_posturep_posture_id_112deff6_fk_evaluatio` (`posture_id`),
  CONSTRAINT `evaluations_posturep_posture_id_112deff6_fk_evaluatio` FOREIGN KEY (`posture_id`) REFERENCES `evaluations_posture` (`id`),
  CONSTRAINT `evaluations_posturephoto_chk_1` CHECK ((`width` >= 0)),
  CONSTRAINT `evaluations_posturephoto_chk_2` CHECK ((`height` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `evaluations_recommendation` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `text` longtext NOT NULL,
  `author_id` bigint NOT NULL,
  `posture_id` bigint NOT NULL,
  `attended_at` datetime(6) DEFAULT NULL,
  `attended_by_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `evaluations_recommen_author_id_6a5229fb_fk_accounts_` (`author_id`),
  KEY `evaluations_recommen_posture_id_334be8f4_fk_evaluatio` (`posture_id`),
  KEY `evaluations_recommen_attended_by_id_09fe31bb_fk_accounts_` (`attended_by_id`),
  CONSTRAINT `evaluations_recommen_attended_by_id_09fe31bb_fk_accounts_` FOREIGN KEY (`attended_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `evaluations_recommen_author_id_6a5229fb_fk_accounts_` FOREIGN KEY (`author_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `evaluations_recommen_posture_id_334be8f4_fk_evaluatio` FOREIGN KEY (`posture_id`) REFERENCES `evaluations_posture` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `evaluations_rulaassessment` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `method` varchar(80) NOT NULL,
  `upper_arm_angle` decimal(4,1) NOT NULL,
  `shoulder_raised` tinyint(1) NOT NULL,
  `upper_arm_abducted` tinyint(1) NOT NULL,
  `arm_supported` tinyint(1) NOT NULL,
  `lower_arm_angle` decimal(4,1) NOT NULL,
  `lower_arm_across_midline_or_out` tinyint(1) NOT NULL,
  `wrist_angle` decimal(4,1) NOT NULL,
  `wrist_bent_from_midline` tinyint(1) NOT NULL,
  `wrist_twist_near_end` tinyint(1) NOT NULL,
  `arm_static_or_repeated` tinyint(1) NOT NULL,
  `arm_load` varchar(30) NOT NULL,
  `neck_angle` decimal(4,1) NOT NULL,
  `neck_twisted` tinyint(1) NOT NULL,
  `neck_side_bent` tinyint(1) NOT NULL,
  `trunk_angle` decimal(4,1) NOT NULL,
  `trunk_supported_seated` tinyint(1) NOT NULL,
  `trunk_twisted` tinyint(1) NOT NULL,
  `trunk_side_bent` tinyint(1) NOT NULL,
  `legs_supported_and_balanced` tinyint(1) NOT NULL,
  `body_static_or_repeated` tinyint(1) NOT NULL,
  `body_load` varchar(30) NOT NULL,
  `partial_scores` json NOT NULL,
  `grand_score` smallint unsigned NOT NULL,
  `action_level` smallint unsigned NOT NULL,
  `photo_id` bigint NOT NULL,
  `posture_id` bigint NOT NULL,
  `ai_suggestion` json NOT NULL DEFAULT (_utf8mb4'{}'),
  PRIMARY KEY (`id`),
  UNIQUE KEY `posture_id` (`posture_id`),
  KEY `evaluations_rulaasse_photo_id_75ecb84e_fk_evaluatio` (`photo_id`),
  CONSTRAINT `evaluations_rulaasse_photo_id_75ecb84e_fk_evaluatio` FOREIGN KEY (`photo_id`) REFERENCES `evaluations_posturephoto` (`id`),
  CONSTRAINT `evaluations_rulaasse_posture_id_f8896eda_fk_evaluatio` FOREIGN KEY (`posture_id`) REFERENCES `evaluations_posture` (`id`),
  CONSTRAINT `assessment_action_level_range` CHECK ((`action_level` between 1 and 4)),
  CONSTRAINT `assessment_grand_score_range` CHECK ((`grand_score` between 1 and 7)),
  CONSTRAINT `evaluations_rulaassessment_chk_1` CHECK ((`grand_score` >= 0)),
  CONSTRAINT `evaluations_rulaassessment_chk_2` CHECK ((`action_level` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `geography_department` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `api_id` int unsigned NOT NULL,
  `name` varchar(80) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `api_id` (`api_id`),
  UNIQUE KEY `name` (`name`),
  CONSTRAINT `geography_department_chk_1` CHECK ((`api_id` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `geography_municipality` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `api_id` int unsigned NOT NULL,
  `name` varchar(100) NOT NULL,
  `department_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `api_id` (`api_id`),
  UNIQUE KEY `municipality_unique_name_in_department` (`department_id`,(lower(`name`))),
  CONSTRAINT `geography_municipali_department_id_b7136376_fk_geography` FOREIGN KEY (`department_id`) REFERENCES `geography_department` (`id`),
  CONSTRAINT `geography_municipality_chk_1` CHECK ((`api_id` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `visits_schedulelock` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `visits_visit` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `scheduled_at` datetime(6) NOT NULL,
  `contact_name` varchar(150) NOT NULL,
  `site_id` bigint NOT NULL,
  `duration_minutes` smallint unsigned NOT NULL,
  `purpose` longtext NOT NULL,
  `contact_phone` varchar(30) NOT NULL,
  `status` varchar(20) NOT NULL,
  `requested_by_id` bigint DEFAULT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  `completed_by_id` bigint DEFAULT NULL,
  `completion_notes` longtext NOT NULL,
  `cancelled_at` datetime(6) DEFAULT NULL,
  `cancelled_by_id` bigint DEFAULT NULL,
  `cancellation_reason` varchar(300) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `visits_visit_site_id_3172f31b_fk_companies_site_id` (`site_id`),
  KEY `visits_visit_requested_by_id_5b289a94_fk_accounts_user_id` (`requested_by_id`),
  KEY `visits_visit_completed_by_id_3f34f3c9_fk_accounts_user_id` (`completed_by_id`),
  KEY `visits_visit_cancelled_by_id_e0c0975d_fk_accounts_user_id` (`cancelled_by_id`),
  KEY `visit_status_start` (`status`,`scheduled_at`),
  CONSTRAINT `visits_visit_cancelled_by_id_e0c0975d_fk_accounts_user_id` FOREIGN KEY (`cancelled_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `visits_visit_completed_by_id_3f34f3c9_fk_accounts_user_id` FOREIGN KEY (`completed_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `visits_visit_requested_by_id_5b289a94_fk_accounts_user_id` FOREIGN KEY (`requested_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `visits_visit_site_id_3172f31b_fk_companies_site_id` FOREIGN KEY (`site_id`) REFERENCES `companies_site` (`id`),
  CONSTRAINT `visit_cancelled_has_reason` CHECK (((`status` <> _utf8mb4'cancelada') or ((`cancelled_at` is not null) and (`cancellation_reason` <> _utf8mb4'')))),
  CONSTRAINT `visit_completed_has_date` CHECK (((`status` <> _utf8mb4'realizada') or (`completed_at` is not null))),
  CONSTRAINT `visit_duration_positive` CHECK ((`duration_minutes` > 0)),
  CONSTRAINT `visits_visit_chk_1` CHECK ((`duration_minutes` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

SET FOREIGN_KEY_CHECKS = 1;
