import weapons from "../data/conan_weapons.json";
import armor from "../data/conan_armor.json";
import thralls from "../data/conan_thralls.json";
import consumables from "../data/conan_consumables.json";

export function GET() {
  const entries = [
    ...weapons.map((w: any) => ({
      title: w.name,
      href: `/weapons/${w.slug}/`,
      sub: `Weapon · dmg ${w.dmg ?? "?"} · ${w.weapon_class || ""}`,
      icon: w.icon_file || "",
    })),
    ...armor.map((a: any) => ({
      title: a.name,
      href: `/armor/${a.slug}/`,
      sub: `Armor · value ${a.armor ?? "?"} · ${a.armor_type || ""}`,
      icon: a.icon_file || "",
    })),
    ...thralls.map((t: any) => ({
      title: t.name,
      href: `/thralls/${t.slug}/`,
      sub: `${t.type || "NPC"} · ${t.hp} HP · ${t.class || ""}`,
      icon: t.icon_file || "",
    })),
    ...consumables.map((c: any) => ({
      title: c.name,
      href: `/consumables/${c.slug}/`,
      sub: `Consumable · heal ${c.heal ?? 0} · food ${c.food ?? 0} · drink ${c.drink ?? 0}`,
      icon: c.icon_file || "",
    })),
  ].sort((a, b) => a.title.localeCompare(b.title));
  return new Response(JSON.stringify(entries), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}
