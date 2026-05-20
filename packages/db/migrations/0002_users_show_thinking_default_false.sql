-- New users default to "show thinking" OFF (collapsed reasoning + summarized
-- inter-agent messages). Changes the column default for FUTURE inserts only;
-- existing rows keep their current value. Idempotent.
ALTER TABLE "macrohero_new"."users"
  ALTER COLUMN "show_thinking" SET DEFAULT false;
