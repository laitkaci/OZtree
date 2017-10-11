import LeafLayoutBase from '../leaf_layout_helper';

import {color_theme} from '../../../themes/color_theme';
import ArcShape from '../../shapes/arc_shape';
import ArcTextShape from '../../shapes/arc_text_shape';
import TextShape from '../../shapes/text_shape';
import PathShape from '../../shapes/path_shape';
import ImageShape from '../../shapes/image_shape';
import BezierShape from '../../shapes/bezier_shape';
import MoveToShape from '../../shapes/move_to_shape';
import LineToShape from '../../shapes/line_to_shape';
import tree_state from '../../../tree_state';
import {get_abs_x, get_abs_y, get_abs_r} from '../utils';
import {global_button_action} from '../../../button_manager';
import {live_area_config} from '../../live_area_config';
import {add_mr} from '../../move_restriction';
import {get_image, image_ready} from '../../../image_cache';
import {extxt, spec_num_full} from '../../../factory/utils';
import config from '../../../global_config';

class LifeLeafLayoutBase extends LeafLayoutBase 
{
    // redefine the leafbase so that we don't get a background coloured slither around the leaf
    fullLeafBase(x,y,r,angle,node,shapes) {
        this.leafBaseLiveAreaTest(x,y,r,node);
        this.randomNaturalLeaf(x,y,r,angle,node,shapes);
        this.hovering = false;
    }

    // Replace the leaf by circles
    naturalLeaf(x,y,r,angle,xtip,ytip,tipd,tipa,node,shapes)
    {    
        let arc_shape = ArcShape.create();
        arc_shape.x = x;
        arc_shape.y = y;
        arc_shape.r = r;
        arc_shape.circle = true;

        let path_shape = PathShape.create();
        if (this.hovering) {
            path_shape.fill.color = color_theme.get_color("leaf.inside_hover.fill", node);  
        } else {
            path_shape.fill.color = color_theme.get_color("leaf.inside.fill", node);  
        }
        path_shape.path_length = 1;
        path_shape.path[0] = arc_shape;
        path_shape.do_fill = true;
        path_shape.height = 4;
        shapes.push(path_shape);
    }

    // Remove the outline
    circularLeafBase(x,y,r,angle,node,shapes) {
        this.leafBaseLiveAreaTest(x,y,r,node);
        //this.circularOutlinedLeaf(x,y,r,r*0.12,node,shapes);
        this.hovering = false;
    }

    // Remove the outline
    ghostLeafBase(x,y,r,angle,node,shapes) {
        if (!this.hovered && this.liveAreaTest(x,y,r)) {
            this.hovered = true;
            this.hovering = true;
            live_area_config.leaf_low_res_leafbase.register_button_event(node);
        }
        let detail_level = 0;
        if (r > 90) {
            detail_level = 3;
        }
        //this.circularDottedLeaf(x,y,r,node,shapes);
        this.hovering = false;
    }

    // No sponsor
    fullLeaf_sponsor(shapes,x,y,r,angle,sponsored,mouseTouch,sponsorText,extraText,commonText,latinText,conservation_text,copyText,imageObject,hasImage,node,requiresCrop,cropMult,cropLeft,cropTop) {        
    }

    // 
    fullLeaf_detail1(shapes,x,y,r,angle,sponsored,mouseTouch,sponsorText,extraText,commonText,latinText,conservation_text,copyText,imageObject,hasImage,node,requiresCrop,cropMult,cropLeft,cropTop) {
        if (r > 20 && r <= 50) {
            if (imageObject) {
                this.circle_cut_image(shapes,imageObject, x, y, r*0.85, color_theme.get_color("leaf.inside.fill",node), null, node);
            } else {
                let text_shape = TextShape.create();
                text_shape.height = 5;
                text_shape.line = 3;
                text_shape.text = commonText ? commonText : latinText;
                text_shape.font_style = commonText ? null : 'italic';
                text_shape.x = x;
                text_shape.y = y;
                text_shape.width = r * 1.25;
                text_shape.defpt = r * 0.3;
                text_shape.min_text_size_extra = 3;
                text_shape.do_fill = true;
                text_shape.fill.color = color_theme.get_color("leaf.text.fill", node);
                shapes.push(text_shape);
            }  
        }
    }

    fullLeaf_detail2(shapes,x,y,r,angle,sponsored,mouseTouch,sponsorText,extraText,commonText,latinText,conservation_text,copyText,imageObject,hasImage,node,requiresCrop,cropMult,cropLeft,cropTop) {
        if (r > 50 && r <= 90) {
            let text_shape = TextShape.create();
            text_shape.height = 5;
            text_shape.min_text_size_extra = 3;
            text_shape.x = x;
            text_shape.do_fill = true;
            text_shape.fill.color = color_theme.get_color("leaf.text.fill",node);
            if (imageObject) {
                text_shape.text = commonText ? commonText : latinText;
                text_shape.font_style = commonText ? null : 'italic';
                text_shape.y = y - r * 0.55;
                text_shape.width = r * 1.1;
                text_shape.defpt = r * 0.15;
                text_shape.line = 2;
                shapes.push(text_shape);
                this.rounded_image(shapes,imageObject, x, y+r*0.2,r*0.95,
                  color_theme.get_color("leaf.inside.fill",node),
                  undefined,
                  requiresCrop,cropMult,cropLeft,cropTop, node);
            } else {
                text_shape.text = commonText ? commonText : latinText;
                text_shape.font_style = commonText ? null : 'italic';
                text_shape.y = y;
                text_shape.width = r * 1.25;
                text_shape.defpt = r * 0.3;
                text_shape.line = 3;
                shapes.push(text_shape);
            }  
        }
    }

    fill_fullleaf_detail3(text_shape, node, r, x) {
        if (this.hovering) {
            text_shape.stroke.color = color_theme.get_color("leaf.text_hover.stroke", node);
            text_shape.stroke.line_cap = 'round';
            text_shape.stroke.line_width = Math.min(17, r*0.06);
            text_shape.do_stroke = true;
        }
        text_shape.height = 5;
        text_shape.min_text_size_extra = 3;
        text_shape.x = x;
        text_shape.do_fill = true;
        text_shape.fill.color = color_theme.get_color("leaf.text.fill", node);
    }

    fullLeaf_detail3(shapes,x,y,r,angle,sponsored,mouseTouch,sponsorText,extraText,commonText,latinText,conservation_text,copyText,imageObject,hasImage,node,requiresCrop,cropMult,cropLeft,cropTop) {
        this.fullLeaf_detail3_conservation(shapes,x,y,r,conservation_text,imageObject,node);
        this.fullLeaf_detail3_names(shapes,x,y,r,commonText,latinText,conservation_text,imageObject,node);
        this.fullLeaf_detail3_pics(shapes,x,y,r,conservation_text,imageObject,requiresCrop,cropMult,cropLeft,cropTop,node)
    }
  
    fullLeaf_detail3_names(shapes,x,y,r,commonText,latinText,conservation_text,imageObject,node) {
        if (r > 90) {
            if (!this.hovered && this.liveAreaTest(x,y,r*0.88)) {
                this.hovered = true;
                this.hovering = true;
                live_area_config.leaf_high_res_text.register_button_event(node);
            }
            let index = 3;
            index -= imageObject ? 2 : 0;
            index -= (conservation_text.length > 0) ? 1 : 0;
            let cl1_y_arr = [0.47, 0.63, -0.5, -0.45];
            let cl2_y_arr = [-0.6, -0.55, 0, 0.2];
            let cl1_line_arr = [1, 2, 2, 2];
            let cl2_line_arr = [2, 2, 2, 3];
            let cl1_width_arr = [1, 1.1, 1.1, 1.1];
            let cl2_width_arr = [1.2, 1.2, 1.5, 1.4];
            let cl1_defpt_arr = [0.1, 0.12, 0.15, 0.15];
            let cl2_defpt_arr = [0.12, 0.15, 0.25, 0.2];
      
            let text_shape = TextShape.create();
            this.fill_fullleaf_detail3(text_shape, node, r, x);
            text_shape.text = commonText ? latinText : OZstrings["No common name"];
            text_shape.font_style = commonText ? 'italic' : null;
            text_shape.y = y + r * cl1_y_arr[index];
            text_shape.width = r * cl1_width_arr[index];
            text_shape.defpt = r * cl1_defpt_arr[index];
            text_shape.line = cl1_line_arr[index];
            shapes.push(text_shape);

            text_shape = TextShape.create();
            this.fill_fullleaf_detail3(text_shape, node, r, x);
            text_shape.text = commonText ? commonText : latinText;
            text_shape.font_style = commonText ? null : 'italic';
            text_shape.y = y + r * cl2_y_arr[index];
            text_shape.width = r * cl2_width_arr[index];
            text_shape.defpt = r * cl2_defpt_arr[index];
            text_shape.line = cl2_line_arr[index];
            shapes.push(text_shape);
            this.hovering = false;
        }
    }
  
    fullLeaf_detail3_conservation(shapes,x,y,r,conservation_text,imageObject,node) {
        if (r > 90 && conservation_text.length > 0) {
            let conservation_hover_test1 = !this.hovered && imageObject && this.liveSquareAreaTest(x-r/2,x+r/2,y+r*0.51,y+r*0.83);
            let conservation_hover_test2 = !this.hovered && !imageObject && this.liveSquareAreaTest(x-r/2,x+r/2,y+r*0.37,y+r*0.71);
            if (conservation_hover_test1 || conservation_hover_test2) {
                this.hovered = true;
                this.hovering = true;
                live_area_config.leaf_conservation_text.register_button_event(node);  
            }
            let text_shape;
            if (imageObject) {
                text_shape = TextShape.create();
                this.fill_fullleaf_detail3(text_shape, node, r, x);
                text_shape.text = conservation_text[0];
                text_shape.y = y + r * 0.575;
                text_shape.width = r;
                text_shape.defpt = r * 0.07;
                shapes.push(text_shape);

                text_shape = TextShape.create();
                this.fill_fullleaf_detail3(text_shape, node, r, x);
                text_shape.text = conservation_text[1];
                text_shape.y = y + r * 0.665;
                text_shape.width = r;
                text_shape.defpt = r * 0.07;
                shapes.push(text_shape);
        
                text_shape = TextShape.create();
                this.fill_fullleaf_detail3(text_shape, node, r, x);
                text_shape.text = conservation_text[2];
                text_shape.y = y + r * 0.755;
                text_shape.width = r;
                text_shape.defpt = r * 0.07;
                shapes.push(text_shape);
            } else {
                text_shape = TextShape.create();
                this.fill_fullleaf_detail3(text_shape, node, r, x);
                text_shape.text = conservation_text[0];
                text_shape.y = y + r * 0.39;
                text_shape.width = r;
                text_shape.defpt = r * 0.1;
                shapes.push(text_shape);
        
                text_shape = TextShape.create();
                this.fill_fullleaf_detail3(text_shape, node, r, x);
                text_shape.text = conservation_text[1];
                text_shape.y = y + r * 0.515;
                text_shape.width = r;
                text_shape.defpt = r * 0.1;
                shapes.push(text_shape);
        
                text_shape = TextShape.create();
                this.fill_fullleaf_detail3(text_shape, node, r, x);
                text_shape.text = conservation_text[2];
                text_shape.y = y + r * 0.64;
                text_shape.width = r;
                text_shape.defpt = r * 0.1;
                shapes.push(text_shape);
            }
            this.hovering = false;
        }
    }

    fullLeaf_detail3_pics(shapes,x,y,r,conservation_text,imageObject,requiresCrop,cropMult,cropLeft,cropTop, node) {
        if (r > 90) {
            if (imageObject && (conservation_text.length > 0)) {
                this.rounded_image(shapes,imageObject,x,y,r*0.75,
                  color_theme.get_color("leaf.inside.fill",node),
                  undefined,
                  requiresCrop,cropMult,cropLeft,cropTop, node);
            } else if (imageObject) {
                this.rounded_image(shapes,imageObject,x,y+r*0.05,r*0.75,
                  color_theme.get_color("leaf.inside.fill",node),
                  undefined,
                  requiresCrop,cropMult,cropLeft,cropTop, node);
            } 
        }
    }
}

export default LifeLeafLayoutBase;