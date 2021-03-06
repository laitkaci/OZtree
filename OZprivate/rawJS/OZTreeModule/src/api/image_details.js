import data_repo from '../factory/data_repo';
import {get_factory} from '../factory/factory';
import api_wrapper from './api_wrapper';
import tree_state from '../tree_state';
import config from '../global_config';


class ImageDetailsAPI {
  constructor() {
    this.size_threshold = 350;
    this.interval = 1000;
  }
  start() {
    this.api = config.api.image_details_api;
    start_fetch_loop(this);
  }
}

function prepare_image_api_data(image_data) {
  let src_id_with_src_1 = [];
  let src_id_with_src_2 = [];
  
  let length = image_data.length;
  for (let i=0; i<length; i++) {
    if (image_data[i].src === "1") {
      src_id_with_src_1.push(image_data[i].src_id);
    } else {
      src_id_with_src_2.push(image_data[i].src_id);
    }
  }
  
  let data = {};
  if (src_id_with_src_1.length > 0) data["1"] = src_id_with_src_1.join(",");
  if (src_id_with_src_2.length > 0) data["2"] = src_id_with_src_2.join(","); 
  
  return data;
}

function prepare_picid_metacode_map(image_data) {
  let picid_metacode_map = {};
  let length = image_data.length;
  for (let i=0; i<length; i++) {
    picid_metacode_map[image_data[i].src_id] = image_data[i].metacode;
  }
  return picid_metacode_map;
}

function fetch_image_detail(root, image_api) {
  if (!tree_state.flying) {
    let image_data = [];
    collect_nodes_need_image_details(root, image_data, image_api);
    let form_data = prepare_image_api_data(image_data);
    let picid_metacode_map = prepare_picid_metacode_map(image_data);
    
    if (Object.keys(form_data).length > 0) {
      let params = {
        url: image_api.api,
        method: 'get',
        data: form_data,
        success: function(res) {
          if (res.image_details) {
            for (let i=0; i<res.image_details.length; i++) {
              let src_id = res.image_details[i][res.headers["src_id"]];
              let rights = res.image_details[i][res.headers["rights"]];
              let licence = res.image_details[i][res.headers["licence"]];
              
              let metacode = picid_metacode_map[src_id];
              data_repo.update_image_metadata(metacode, rights, licence);
            }
          }
        },
        error: function() {
          console.error("error when fetching image details " + data);
        }
      }  
      api_wrapper(params);
    }    
  }
}

/**
 * Fetching image details every image_api.interval milliseconds.
 */
function start_fetch_loop(image_api) {
  let root = get_factory().get_root();
  if (root) {
    fetch_image_detail(root, image_api);
  } 
  setTimeout(function() {
    start_fetch_loop(image_api);
  }, image_api.interval);
}


/**
 * This percolates down the tree and collects image details from nodes that are 
 * sufficiently large.
 * The problem is that this then doesn't fetch the copyright details for 
 * internal node pictures. This needs fixing somehow.
 *
 * Yan has mentioned maybe collect nodes which need image details while refreshing the canvas. 
 * Kai thinks that it is not critical as the cost for collecting nodes are very small, averaging less than 0.1 milliseconds.
 * Besides, if collect these nodes while refreshing, then the test in this function would run in each frame, which would makes each frame
 * more costly.
 */
function collect_nodes_need_image_details(node, arr, image_api) {
  if (node.dvar) {
    let visible_and_big = node.gvar && node.rvar > image_api.size_threshold;
    let detail_fetched_except_pic_credit = node.is_leaf && node.detail_fetched && node.pic_filename && !node.pic_credit;
    
    if (visible_and_big && detail_fetched_except_pic_credit) {
      arr.push({
        src_id: node.pic_filename,
        src: node.pic_src,
        metacode: node.metacode
      });
    }
    if (node.has_child && node.rvar && node.rvar > image_api.size_threshold) {
      let length = node.children.length;
      for (let i=0; i<length; i++) {
        collect_nodes_need_image_details(node.children[i], arr, image_api);
      }
    }      
  }
}



let image_details_api = new ImageDetailsAPI();
export default image_details_api;
