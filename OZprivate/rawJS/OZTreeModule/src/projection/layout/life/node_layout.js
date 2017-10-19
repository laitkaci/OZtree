import NodeLayoutBase from '../node_layout_helper';
import config from '../../../global_config';

import tree_state from '../../../tree_state';
import {color_theme} from '../../../themes/color_theme';
import ArcShape from '../../shapes/arc_shape';
import TextShape from '../../shapes/text_shape';
import ImageShape from '../../shapes/image_shape';
import ArcTextShape from '../../shapes/arc_text_shape';
import {ageAsText, gpmapper, is_primary_or_secondary_name} from '../../../factory/utils';
import {add_mr} from '../../move_restriction';
import {global_button_action} from '../../../button_manager';
import {live_area_config} from '../../live_area_config';

class LifeNodeLayout extends NodeLayoutBase
{
    calc_twh(node) {
        this.twidth = config.projection.Twidth * (config.projection.partc - config.projection.partl2) * node.rvar;  
        this.theight = config.projection.Tsize  * (config.projection.partc - config.projection.partl2) / 2.0 * node.rvar;
        this.theight2 = config.projection.Tsize  * (config.projection.partc - config.projection.partl2) / 3.0 * node.rvar;
    }

    autopic_set_shapes(node, x, y, width, height, shapes) 
    {
        let radiusr = 0.2 * config.image_scale_node * width ;

        // get a random picture
        if (node.image_index === undefined)
            node.image_index = Math.floor(node.num_pics * Math.random());       
        let pic_info = node.get_picset_src_info(node.image_index);

        // draw it
        let arc_shape = ArcShape.create();
        arc_shape.x = x;
        arc_shape.y = y;
        arc_shape.circle = true;
        arc_shape.r = radiusr;
      
        let image_shape = ImageShape.create();
        image_shape.src = pic_info[0];
        image_shape.filename = pic_info[1];
        image_shape.x = x - radiusr;
        image_shape.y = y - radiusr;
        image_shape.w = radiusr * 2;
        image_shape.h = radiusr * 2;
        image_shape.clip = arc_shape; 
        image_shape.height= 5;
        shapes.push(image_shape);
    }

    interior_circle_shapes(node, shapes) {   
        // uncomment this to get guidelines
        /*
        let horizonarc = ArcShape.create();
        if (!this.hovered && this.live_area_interior_circle_test(node)) {
            this.hovered = true;
            this.hovering = true;
            live_area_config.interior_low_res_circle.register_button_event(node);
        }
        horizonarc.x = node.xvar + node.rvar * node.arcx;
        horizonarc.y = node.yvar + node.rvar * node.arcy;
        horizonarc.r = node.rvar;
        horizonarc.circle = true;
        horizonarc.height = 2;
        horizonarc.order = "fill_first";
        horizonarc.do_stroke = true;
        horizonarc.stroke.line_width = 1;
        horizonarc.stroke.color = color_theme.get_color('interior.circle.stroke', node);
        shapes.push(horizonarc);
        */
    }
}

export default LifeNodeLayout;