# Contract schema compatibility

Compatibility modes are `strict`, `backward`, `forward`, `full`, and `custom_bounded`. Strict rejects structural differences. Backward permits known safe widening and nullable additions while rejecting removals, narrowing, and tightened nullability. Forward/full are evaluated only where provider semantics supply evidence. Unsupported or absent type semantics return `unknown`, never compatible. Custom exceptions are bounded declarative values; executable code and unrestricted regex/SQL are prohibited.
