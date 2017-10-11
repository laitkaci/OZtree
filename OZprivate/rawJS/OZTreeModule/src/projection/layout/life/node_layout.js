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

export default NodeLayoutBase;