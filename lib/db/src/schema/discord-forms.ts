import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";
import {
  bigint,
  boolean,
  index,
  integer,
  pgTable,
  serial,
  text,
  timestamp,
  uniqueIndex,
  varchar,
} from "drizzle-orm/pg-core";

export const discordFormSectionsTable = pgTable(
  "discord_form_sections",
  {
    id: serial("id").primaryKey(),
    guildId: bigint("guild_id", { mode: "bigint" }).notNull(),
    slug: varchar("slug", { length: 50 }).notNull(),
    title: varchar("title", { length: 100 }).notNull(),
    staffChannelId: bigint("staff_channel_id", { mode: "bigint" }),
    embedColor: integer("embed_color").notNull().default(0x2e86de),
    imageUrl: text("image_url"),
    active: boolean("active").notNull().default(true),
    createdBy: bigint("created_by", { mode: "bigint" }).notNull(),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (table) => ({
    guildSlugUnique: uniqueIndex("discord_form_sections_guild_slug_unique").on(
      table.guildId,
      table.slug,
    ),
    guildActiveIndex: index("discord_form_sections_guild_active_idx").on(
      table.guildId,
      table.active,
    ),
  }),
);

export const discordFormQuestionsTable = pgTable(
  "discord_form_questions",
  {
    id: serial("id").primaryKey(),
    sectionId: integer("section_id")
      .notNull()
      .references(() => discordFormSectionsTable.id, { onDelete: "cascade" }),
    position: integer("position").notNull(),
    prompt: varchar("prompt", { length: 45 }).notNull(),
    inputStyle: varchar("input_style", { length: 12 })
      .notNull()
      .default("short"),
    placeholder: varchar("placeholder", { length: 100 }),
    required: boolean("required").notNull().default(true),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (table) => ({
    sectionPositionIndex: index("discord_form_questions_section_position_idx").on(
      table.sectionId,
      table.position,
    ),
  }),
);

export const discordFormButtonsTable = pgTable(
  "discord_form_buttons",
  {
    id: varchar("id", { length: 36 }).primaryKey(),
    guildId: bigint("guild_id", { mode: "bigint" }).notNull(),
    sectionId: integer("section_id")
      .notNull()
      .references(() => discordFormSectionsTable.id, { onDelete: "cascade" }),
    channelId: bigint("channel_id", { mode: "bigint" }).notNull(),
    messageId: bigint("message_id", { mode: "bigint" }).notNull(),
    label: varchar("label", { length: 80 }).notNull(),
    style: varchar("style", { length: 12 }).notNull().default("primary"),
    customId: varchar("custom_id", { length: 100 }).notNull().unique(),
    active: boolean("active").notNull().default(true),
    createdBy: bigint("created_by", { mode: "bigint" }).notNull(),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (table) => ({
    messageUnique: uniqueIndex("discord_form_buttons_message_unique").on(
      table.messageId,
    ),
    guildActiveIndex: index("discord_form_buttons_guild_active_idx").on(
      table.guildId,
      table.active,
    ),
  }),
);

export const insertDiscordFormSectionSchema = createInsertSchema(
  discordFormSectionsTable,
).omit({ id: true, createdAt: true });
export const insertDiscordFormQuestionSchema = createInsertSchema(
  discordFormQuestionsTable,
).omit({ id: true, createdAt: true });
export const insertDiscordFormButtonSchema = createInsertSchema(
  discordFormButtonsTable,
).omit({ createdAt: true });

export type InsertDiscordFormSection = z.infer<
  typeof insertDiscordFormSectionSchema
>;
export type DiscordFormSection = typeof discordFormSectionsTable.$inferSelect;
export type InsertDiscordFormQuestion = z.infer<
  typeof insertDiscordFormQuestionSchema
>;
export type DiscordFormQuestion = typeof discordFormQuestionsTable.$inferSelect;
export type InsertDiscordFormButton = z.infer<
  typeof insertDiscordFormButtonSchema
>;
export type DiscordFormButton = typeof discordFormButtonsTable.$inferSelect;
