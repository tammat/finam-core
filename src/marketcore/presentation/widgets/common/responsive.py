from __future__ import annotations


class Responsive:
    @staticmethod
    def css() -> str:
        return """
<style>
.mc-grid{display:grid;grid-template-columns:repeat(12,1fr);gap:16px}
.mc-span-12{grid-column:span 12}.mc-span-6{grid-column:span 6}
.mc-span-4{grid-column:span 4}.mc-span-3{grid-column:span 3}
@media(max-width:1024px){.mc-grid{grid-template-columns:repeat(8,1fr)}
.mc-span-6,.mc-span-4,.mc-span-3{grid-column:span 8}}
@media(max-width:768px){.mc-grid{grid-template-columns:repeat(4,1fr);gap:12px}
.mc-span-12,.mc-span-6,.mc-span-4,.mc-span-3{grid-column:span 4}
.fc-card{padding:12px}.fc-metric{font-size:22px}}
</style>
"""

    @staticmethod
    def grid(class_name: str = "responsive-grid") -> str:
        return class_name

    @staticmethod
    def card(class_name: str = "responsive-card") -> str:
        return class_name

    @staticmethod
    def table(class_name: str = "responsive-table") -> str:
        return class_name

    @staticmethod
    def stack(class_name: str = "responsive-stack") -> str:
        return class_name
