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

    // No highlight
    circle_cut_image(shapes,imageObject,centerpointx,centerpointy,radiusr,borderColor,highlightColor, node) {
        if (imageObject) {
     
            let arc_shape = ArcShape.create();
            arc_shape.x = centerpointx;
            arc_shape.y = centerpointy;
            arc_shape.circle = true;
            arc_shape.r = radiusr;
      
            let image_shape = ImageShape.create();
            image_shape.img = imageObject;
            image_shape.x = centerpointx - radiusr;
            image_shape.y = centerpointy - radiusr;
            image_shape.w = radiusr * 2;
            image_shape.h = radiusr * 2;
            image_shape.clip = arc_shape; 
            image_shape.height= 5;
            shapes.push(image_shape);
        }
    }

    // Draw an opaque image
    circle_cut_image_opaque(shapes,imageObject,centerpointx,centerpointy,radiusr,borderColor,highlightColor, node)
    {
        let alpha = config.image_opacity;
        config.image_opacity = 1;
        this.circle_cut_image(shapes,imageObject, centerpointx, centerpointy, radiusr, borderColor, highlightColor, node);
        config.image_opacity = alpha;
    }

    // Draw Image in Fullsize
    fullLeaf_detail1(shapes,x,y,r,angle,sponsored,mouseTouch,sponsorText,extraText,commonText,latinText,conservation_text,copyText,imageObject,hasImage,node,requiresCrop,cropMult,cropLeft,cropTop) {
        if (r > 20 && r <= 50) {
            if (imageObject) {
                this.circle_cut_image_opaque(shapes,imageObject, x, y, r, color_theme.get_color("leaf.inside.fill",node), null, node);
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

    // Draw Image in Fullsize
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
                this.circle_cut_image_opaque(shapes,imageObject, x, y, r, color_theme.get_color("leaf.inside.fill",node), null, node);
                shapes.push(text_shape);
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

    // Draw Text on Top
    fullLeaf_detail3(shapes,x,y,r,angle,sponsored,mouseTouch,sponsorText,extraText,commonText,latinText,conservation_text,copyText,imageObject,hasImage,node,requiresCrop,cropMult,cropLeft,cropTop) {
        this.fullLeaf_detail3_pics(shapes,x,y,r,conservation_text,imageObject,requiresCrop,cropMult,cropLeft,cropTop,node)
        this.fullLeaf_detail3_conservation(shapes,x,y,r,conservation_text,imageObject,node);
        this.fullLeaf_detail3_names(shapes,x,y,r,commonText,latinText,conservation_text,imageObject,node);
    }

    // Draw Image in Fullsize
    fullLeaf_detail3_pics(shapes,x,y,r,conservation_text,imageObject,requiresCrop,cropMult,cropLeft,cropTop, node) {
        if (r > 90) {
            if (imageObject) {
                this.circle_cut_image_opaque(shapes,imageObject, x, y, r, color_theme.get_color("leaf.inside.fill",node), null, node);
            }
        }
    }

    // Make the circle full
    circle_leaf_shapes(node, shapes) {
        add_mr(this.get_leaf_x(node), this.get_leaf_y(node), this.get_leaf_radius(node));
        let arc_shape = ArcShape.create();
        arc_shape.x = node.xvar + node.rvar * node.arcx;
        arc_shape.y = node.yvar + node.rvar * node.arcy;
        arc_shape.r = node.rvar * node.arcr;
        arc_shape.circle = true;
        arc_shape.height = 2;
        arc_shape.do_fill = true;
        arc_shape.fill.color = color_theme.get_color("leaf.inside.fill", node);
        shapes.push(arc_shape);
    }
}

export default LifeLeafLayoutBase;