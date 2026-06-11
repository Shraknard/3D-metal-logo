// Parametric: exports ONE part per run (relief OR backing) — no boolean union,
// so STL export stays fast. generate.py runs this twice and concatenates the
// two STLs; the overlapping volumes are unioned by the slicer at print time.
//
// Both SVGs share one canvas, imported center=false into the SAME frame, then
// translated by the RELIEF content centre and scaled so content width == target_w.
// import() returns mm directly (1 SVG unit -> k mm).

file        = "";    // relief SVG (absolute path)
backing_file = "";   // backing SVG (absolute path)
target_w    = 120;   // final relief width, mm
text_h      = 3.0;   // relief height, mm
base_h      = 1.6;   // backing thickness, mm
part        = 0;     // 0 relief | 1 backing offset (file) | 2 backing hull | 3 rectangle

k           = 0.352778;  // mm per SVG unit
cx          = 0;         // relief content centre x (SVG units)
cy          = 0;         // relief content centre y (SVG units)
content_w   = 1;         // relief content width  (SVG units)
content_h   = 1;         // relief content height (SVG units)
rect_marg   = 5;         // rectangle plaque margin, mm
$fn         = 6;

s = target_w / (content_w * k);

module placed(f)
    scale([s, s, 1])
        translate([-cx * k, -cy * k, 0])
            import(f, center = false);

if (part == 0)
    linear_extrude(height = text_h) placed(file);
else if (part == 1)
    linear_extrude(height = base_h) placed(backing_file);
else if (part == 2)
    linear_extrude(height = base_h) hull() placed(file);
else if (part == 3)
    linear_extrude(height = base_h)
        square([target_w + 2 * rect_marg,
                content_h * k * s + 2 * rect_marg], center = true);
