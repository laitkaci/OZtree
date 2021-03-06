# -*- coding: utf-8 -*-
import unicodedata
import string
import sys
import re
from OZfunctions import get_common_names
"""
This contains the API functions - node_details, image_details, search_names, and search_sponsors. search_node also exists, which is a combination of search_names and search_sponsors.
# request.vars:
# -- node_ids: '1,2,3'
# -- leaf_ids: '2,3,4'
# -- image_source: 'best_any' or 'best_verified' or 'best_pd'
# -- question: should this contain the 'linkouts' functions, which are also a sort of API.

We should probably compile all docstrings in these files into markdown documentation
"""

def node_details():
    """
    This is the main API call, and should be optimized to within an inch of its life. Some ideas:
    1) Move it to another process (not web2py). E.g. Falcon. See http://klen.github.io/py-frameworks-bench/
    2) Put some of the load on the SQL server, but adding SQL joins rather than making 7 queries (but mysql does not support full outer joins, which we would need)
    3) split the call into 'detailed' and 'non detailed' versions, where the 'detailed' version is only called when e.g. image licence / 
    """
    session.forget(response)
    response.headers["Access-Control-Allow-Origin"] = '*'
    try:
        leafIndices = request.vars.leaf_ids or "" 
        nodeIndices = request.vars.node_ids or ""
        if re.search("[^\d,]", leafIndices) or re.search("[^\d,]", nodeIndices):
            raise #list of ids must only consist of digits and commas, otherwise this is a malicious API call
        if re.search("^,|,$|,,", leafIndices) or re.search("^,|,$|,,", nodeIndices):
            raise #ban sequential commas, or commas at beginning or end - don't do a 'split' as we are going to pass this string straight to SQL for speed
        imageSource = str(request.vars.get('image_source') or "")
        if imageSource != "best_verified" and imageSource != "best_pd":
            imageSource = "best_any" #sanitize - only allowed 3 settings

        language = request.vars.lang or request.env.http_accept_language or 'en'
        first_lang = language.split(',')[0]
        lang_primary = first_lang.split("-")[0]
        nodeOtts = set()
        nodeNames = set()
        leafOtts = set()
        leafNames = set()
    
    
        #Get nodes first and collect OTTs for looking up vernaculars. These contain leaf otts in the representative pictures
        base_ncols = ["id","ott","popularity","age","name","iucnNE","iucnDD","iucnLC","iucnNT","iucnVU","iucnEN","iucnCR","iucnEW","iucnEX"]
        pic_ncols = ["{pic}1","{pic}2","{pic}3","{pic}4","{pic}5","{pic}6","{pic}7","{pic}8"]
        pic_col_name = {"best_any":"rep", "best_verified":"rtr","best_pd":"rpd"}[imageSource]
        all_ncols = base_ncols+pic_ncols
        node_cols = {nm:index for index,nm in enumerate(all_ncols)} 
        if nodeIndices:
            query1 = "SELECT " + ",".join(all_ncols) + " FROM ordered_nodes WHERE id IN ({user_input})"
            sql = query1.format(pic=pic_col_name, user_input=nodeIndices) #must take extreme care here that user_input has been sanitized
            ordered_nodes_query_res = db.executesql(sql)
            for row in ordered_nodes_query_res:
                if row[node_cols['ott']]:
                    nodeOtts.add(str(row[node_cols['ott']]))
                elif row[node_cols['name']]: #use name rather than ott if ott does not exist
                    nodeNames.add(row[node_cols['name']])

                for i in range(len(base_ncols), len(base_ncols)+len(pic_ncols)):
                    if row[i]:
                        leafOtts.add(str(row[i]))
        else:
            ordered_nodes_query_res = []
        #Get leaves next, and add their otts to the leaf pool, for looking up vernaculars and images
        all_lcols = ["id","ott","popularity","name","extinction_date","price"]
        leaf_cols = {nm:index for index,nm in enumerate(all_lcols)} 
        conditions = []
        if leafIndices:
            conditions.append("id IN ({user_input})".format(user_input=leafIndices)) #must take extreme care here that user_input has been sanitized
        if len(leafOtts):
            conditions.append("ott IN ({otts_from_pics})".format(otts_from_pics=",".join(leafOtts)))
        if len(conditions):
            query2 = "SELECT " + ",".join(all_lcols) + " FROM ordered_leaves"
            query2 += " WHERE " + " OR ".join(conditions)
            sql = query2
            ordered_leaves_query_res = db.executesql(sql)
            for row in ordered_leaves_query_res:
                if row[leaf_cols['ott']]:
                    leafOtts.add(str(row[leaf_cols['ott']]))
                elif row[leaf_cols['name']]:
                    leafNames.add(row[leaf_cols['name']])
        else:
            ordered_leaves_query_res = []
        
        #find vernaculars (could be from leaves or nodes)
        #the logic for finding *which* vernaculars to use is in javascript
        #e.g. we probably want to return all 'en-XXX' values, even if the language is en-GB
        #then choose en-GB, en (plain) and en-OTHER in that order
        if len(nodeOtts) + len(leafOtts):
            query3 = "SELECT ott,vernacular FROM vernacular_by_ott WHERE ott IN ({otts})"
            query3 += " AND lang_primary={}".format(db.placeholder)
            query3 += " AND preferred=TRUE ORDER BY src"
            sql = query3.format(otts=",".join(nodeOtts | leafOtts))
            vernacular_name_query_res = db.executesql(sql, (lang_primary,))
        else:
            vernacular_name_query_res = []
        if len(nodeNames) + len(leafNames):
            names = nodeNames | leafNames
            query4 = "SELECT name,vernacular FROM vernacular_by_name WHERE lang_primary={}".format(db.placeholder)
            query4 += " AND name IN (" + ','.join([db.placeholder]*len(names)) + ")"
            query4 += " AND preferred=TRUE"
            sql = query4
            vernacular_name_query_res2 = db.executesql(sql, [lang_primary]+list(names))
        else:
            vernacular_name_query_res2 = []
        
        #find pictures, iucn, and reservation details (only from leaves)
        images_by_ott_query_res = iucn_query_res = reservations_res = {} #don't bother getting images for nodes without otts
        all_pcols = ["ott", "src_id", "src", "rating"]
        all_rcols = ["OTT_ID", "verified_kind", "verified_name", "verified_more_info", "verified_url"]
        alt_rtxt = {"verified_name":"'leaf_sponsored'",
                     "verified_more_info":"''",
                     "verified_url":"NULL"}
        pic_cols = {nm:index for index,nm in enumerate(all_pcols)} 
        res_cols = {nm:index for index,nm in enumerate(all_rcols)} 
        if len(leafOtts):
            ott_ids = ",".join(leafOtts) #must be sure there that these are all integers
            query5 = "SELECT " + ",".join(all_pcols) + " FROM images_by_ott WHERE ott in ({otts})"
            query5 += " AND " + imageSource + " = TRUE"
            sql = query5.format(otts=ott_ids)
            # a bit of python hacking here, so that the best src is returned - annoyingly hard to do in SQL
            images_by_ott_query_res = db.executesql(sql)
            query6 = "SELECT ott,status_code FROM iucn WHERE ott in ({otts})"
            sql = query6.format(otts=ott_ids)
            iucn_query_res = db.executesql(sql)
            query7 = "SELECT "
            #a very complicated query here, use alternative text if this is not an active node (waiting verification or expired)
            query7 += ",".join(["IF(active,{0},{1}) as {0}".format(nm, alt_rtxt[nm]) if nm in alt_rtxt else nm for nm in all_rcols])
            query7 += " FROM (SELECT " + ",".join(all_rcols) + ",(DATE_ADD(verified_time, INTERVAL sponsorship_duration_days DAY) > CURDATE()) AS active FROM reservations"
            query7 += " WHERE OTT_ID in ({otts}) AND verified_time IS NOT NULL AND (deactivated IS NULL OR deactivated = '')"
            query7 += ") AS t"
            sql = query7.format(otts=ott_ids)
            reservations_res = db.executesql(sql)
            
        if nodeIndices or leafIndices:
            res = {"nodes": ordered_nodes_query_res or [], "leaves": ordered_leaves_query_res or [], "lang":language,
                "vernacular_by_ott": vernacular_name_query_res or [], "vernacular_by_name":vernacular_name_query_res2 or [],   
               "leafIucn": iucn_query_res or [], "leafPic": images_by_ott_query_res or [], "reservations": reservations_res or []}
        else:
            #we didn't pass any ids in, so we simply output a list of the column names for the various arrays. The client can thus make a blank call
            #at the start of a session, and get the column names for later use. We don't need e.g. vernacular or IUCN col names, as these simply map ott or names to a string, as [ott, string]
            #it's only the leaves, nodes, pics, and reservations that have more complex details needed.
            #we also pass out the same values as a call with no IDs, to avoid js errors if accidentally no ids are passed in
            res = {"colnames_nodes": node_cols, "colnames_leaves": leaf_cols, 
                   "colnames_images": pic_cols, "colnames_reservations": res_cols,
                   "nodes": [], "leaves": [], "lang":language,
                   "vernacular_by_ott": [], "vernacular_by_name": [],   
                   "leafIucn": [], "leafPic": [], "reservations":[]
                  }
    except: #e.g. if bad data has been passed in
        res = {}
    return res

def image_details():
    """
    e.g. image_details.json?2=25677433,27724652&1=31925837,-1
    where 1 and 2 are src names
    """
    session.forget(response)
    response.headers["Access-Control-Allow-Origin"] = '*'
    try:
        all_cols = ['src', 'src_id', 'rights','licence']
        col_names = {nm:index for index,nm in enumerate(all_cols)}
        queries = []
        for v in request.vars:
            if v.isdigit() and int(v) in inv_src_flags:
                ids = request.vars[v]
                if re.search("[^-\d,]", ids):
                    raise #list of ids must only consist of digits and commas, otherwise this is a malicious API call
                if re.search("^,|[-,]$|,,|-[-,]|\d-", ids):
                    raise #ban commas at start, and before other commas, ban minus signs and commas at end, 
                #if we get here, ids should only contain numbers (negative or positive) with commas between
                q = "(SELECT " + ",".join(all_cols) + " FROM {} WHERE src = {} AND src_id IN({}))"
                queries.append(q.format('images_by_ott',v, ids))
                queries.append(q.format('images_by_name',v, ids))
        return {'headers':col_names, 'image_details': db.executesql(" UNION ALL ".join(queries)) if queries else []}
    except: #e.g. if bad data has been passed in
        res = {}
    return res

#Search
def search_node():
    """
    searches both taxon name (latin & vernacular) and sponsor text, but only looks for sponsors when the number of taxa returned is low
    So that we don't pollute the taxon searches with lots of sponsorship stuff
    """
    session.forget(response)
    response.headers["Access-Control-Allow-Origin"] = '*'
    searchFor = request.vars.query
    res1 = search_for_name()
    if len(res1['leaf_hits']) + len(res1['node_hits']) <15:
        res2 = search_sponsor(searchFor, "all")
    else:
        res2 = {"reservations": {}, "nodes": {}, "leaves": {}}
    return {"nodes": res1, "sponsors": res2}

def search_init():
    """
    This is called at the very start of loading a tree view page. It finds
    request.vars one of:
    -- Number: ott
    -- String: name
    return node or leaf id given ott number or scientific name
    
    The logic here isn;t quite right: if we have multiple OTT hits, we should choose the one
    with the 'nearest' name. At the moment we choose only based on name (with no OTT considerations)
    
    """
    session.forget(response)
    try:
        ott = int(request.vars.get('ott'))
        query = db.ordered_leaves.ott == ott
        leaf_hit = db(query).select(db.ordered_leaves.id)
        if len(leaf_hit) == 1:
            return {"id": -leaf_hit[0].id}
        
        query = db.ordered_nodes.ott == ott
        node_hit = db(query).select(db.ordered_nodes.id)
        if len(node_hit) == 1:
            return {"id": node_hit[0].id}
            
        raise  #if not found ott, go to except branch.
    except:         
        if request.vars.name is not None and len(request.vars.name) > 0:
            tidy_latin = request.vars.name.replace("_", " ")
            query = db.ordered_leaves.name == tidy_latin
            leaf_hits = db(query).select(db.ordered_leaves.id).first()
            if leaf_hits:
                return {"id": -leaf_hits.id}
            
            query = db.ordered_nodes.name == request.vars.name
            node_hits = db(query).select(db.ordered_nodes.id).first()
            if node_hits:
                return {"id": node_hits.id}
    return {"empty": request.vars.ott}


# request.vars contains:
#  -- String: query
#  -- String: 'lang' (default 'en') - used to override the default of request.env.http_accept_language
#  -- Boolean: 'sorted' (default False)
#  -- Number: 'limit'
#  -- Number: 'page' (default 0)
#  -- Boolean: 'include_price' (default False)
#  -- String: 'restrict_tables is one of 'leaves', 'nodes' or None.(default None)
#  Sanitize parameters and then do actually search.
def search_for_name():
    response.headers["Access-Control-Allow-Origin"] = '*'
    try:
        searchFor = str(request.vars.query or "")
        language = request.vars.lang or request.env.http_accept_language or 'en'
        order = True if (request.vars.get('sorted')) else False
        limit=request.vars.get('limit')
        start =request.vars.get('start') or 0
        include_price = True if (request.vars.get('include_price')) else False
        restrict_tables = request.vars.get('restrict_tables')
        return search_by_name(searchFor, language, order_by_popularity = order, limit=limit, start=start, restrict_tables=restrict_tables,include_price=include_price)
    except:
        return dict()
    

def search_by_name(searchFor, language='en', order_by_popularity=False, limit=None, start=0, restrict_tables=None, include_price=False):
    """
    Search in latin and common names for species. To look only in leaves, set restrict_tables to 'leaves'.
    To look only in nodes set it to 'nodes', otherwise we default to searching in both
    """
    """
    1. if string length < 3, then it would run a start match. For example, search for 'zz' would return 'zz plant', search for 'ox ox' would
    return 'ox oxon'(if it exists)
    2. all words' length >= 3, then it would run natural language search on each word.
    3. parts of the words' length >= 3, then it would do a natural language search on these words and then do a containing search on the rest words.
    4. TO DO: substitute all punctuation with spaces (except apostrophe, dash, dot & 'times'
    5. TO DO: in English, we should remove apostrophe-s at the end of a word
    """
    lang_primary = language.split(',')[0].lower().split("-")[0]
    base_colnames = ['id','ott','name','popularity']
    if include_price:
        base_colnames += ['price']
    colnames = base_colnames + ['vernacular','extra_vernaculars']
    colname_map = {nm:index for index,nm in enumerate(colnames)}

    try:
        originalSearchFor = searchFor
        searchFor = searchFor.replace("_", " ").split()
        if len(searchFor)==0:
            raise
        longWords = []
        shortWords = []
        for word in searchFor:
            if len(word) >= 3:
                longWords.append(word)
            else:
                shortWords.append(word)
            
        searchForCommon = " ".join(["+*" + word + "*" for word in longWords])
        searchForLatin = searchForCommon
        
        #Double percentage sign to escape %.
        searchForShortContains = " ".join(["and {0} like '%%" + word + "%%'" for word in shortWords])
        names=set()
        otts=set()
        
        #query the matches against latin and vernaculars in one go, and 
        #http://stackoverflow.com/questions/7082522/using-sql-join-and-union-together
        if restrict_tables=="leaves":
            results={'ordered_leaves':[]}
        elif restrict_tables=="nodes":
            results={'ordered_nodes':[]}
        else:
            results={'ordered_leaves':[], 'ordered_nodes':[]}
        
        for tab in results:
            initial_cols = ",".join(base_colnames)
            if tab=="ordered_nodes":
                initial_cols = initial_cols.replace("price", "NULL AS price") #nodes don't have a price
            query = 'select ' + initial_cols + ' from ' + tab + ' {0}'
            query += ' union select ' + initial_cols + ' from ' + tab + ' where ott in (select distinct ott from vernacular_by_ott {1})'
            query += ' union select ' + initial_cols + ' from ' + tab + ' where name in (select distinct name from vernacular_by_name {2})'
            
            if len(longWords)>0:
                query = query.format(
                    'where match(name) against({0} in boolean mode) ' + searchForShortContains.format('name'),
                    'where match(vernacular) against({0} in boolean mode) and lang_primary={0} ' + searchForShortContains.format('vernacular'),
                    'where match(vernacular) against({0} in boolean mode) and lang_primary={0} ' + searchForShortContains.format('vernacular')
                )
            else:
                query = query.format(
                    "where name like {0}",
                    "where lang_primary={0} and vernacular like {0}",
                    "where lang_primary={0} and vernacular like {0}"
                )
            if order_by_popularity:
                query += ' ORDER BY popularity DESC'
            if limit:
                query += ' LIMIT ' + str(int(limit))
                if start:
                    query += ' OFFSET ' + str(int(start))
            
            
            if len(longWords)>0:
                results[tab] = [list(row) for row in db.executesql(query.format(db.placeholder), (searchForLatin, searchForCommon, lang_primary, searchForCommon, lang_primary))]
            else:
                temp = originalSearchFor + "%%"
                results[tab] = [list(row) for row in db.executesql(query.format(db.placeholder), (temp, lang_primary, temp, lang_primary, temp))]
            #search for common name
            for row in results[tab]:
                if row[1]:
                    otts.add(row[1])
                elif row[2]:
                    names.add(row[2])
        
        #now find the vernacular names for these, so we can  save them in 'vernaculars' and 'extra_vernaculars'
        if len(otts):
            #save the match status in the query return, so we can use it later.
            if len(longWords)>0:
                mtch = 'if(match(vernacular) against({} in boolean mode), TRUE, FALSE) as mtch'
                query = ("select ott,vernacular,preferred,mtch from (select ott, vernacular, preferred, src, " + mtch + " from vernacular_by_ott where lang_primary={} and ott in ({})) t where (mtch or preferred) order by preferred DESC,src").format(db.placeholder, db.placeholder, ",".join([db.placeholder]*len(otts)))
                temp = db.executesql(query, [searchForCommon] + [lang_primary] + list(otts))
            else:
                mtch = "if(vernacular like {}, TRUE, FALSE) as mtch"
                query = ("select ott,vernacular,preferred,mtch from (select ott, vernacular, preferred, src, " + mtch + " from vernacular_by_ott where lang_primary={} and ott in ({})) t where mtch order by preferred DESC,src")
                query = query.format(db.placeholder, db.placeholder, ",".join([db.placeholder]*len(otts)))
                temp = db.executesql(query, [originalSearchFor+'%%'] + [lang_primary] + list(otts))                
            ott_to_vern = {}

            for row in temp:
                if row[0] not in ott_to_vern: #nothing saved yet
                    if row[2]: #this is a preferred match, and is the first preferred encountered, so is the standard vernacular
                        if row[3]: #this is a match, so we don't need to store any non-preferred versions
                            ott_to_vern[row[0]]=[row[1]]
                        else:      #save space for non-preferred matches: there must be at least one, unless the match was via sciname
                            ott_to_vern[row[0]]=[row[1],[]]   
                    else:      #this is not preferred: no standard vernacular, save as an extra
                        ott_to_vern[row[0]]=[None,[row[1]]]
                else:
                    #the entry exists, so we must have already filled out some vernaculars
                    if row[3] and len(ott_to_vern[row[0]])==2: #another match, and standard vernacular didn't match: add to extras
                        ott_to_vern[row[0]][1].append(row[1])
        if len(names):
            #same again, but match on name
            query = "select name,vernacular,preferred,mtch from (select name, vernacular, preferred, src, if(match(vernacular) against({} in boolean mode), TRUE, FALSE) as mtch from vernacular_by_name where lang_primary={} and name in ({})) t where (mtch or preferred) order by preferred DESC,src".format(db.placeholder,db.placeholder,",".join([db.placeholder]*len(names)))
            name_to_vern = {}
            for row in db.executesql(query, [searchForCommon] + [lang_primary] + list(names)):
                if row[0] not in name_to_vern: #nothing saved yet
                    if row[2]: #this is a preferred match, and is the first preferred encountered, so is the standard vernacular
                        if row[3]: #this is a match, so we don't need to store any non-preferred versions
                            name_to_vern[row[0]]=[row[1]]
                        else:      #save space for non-preferred matches: there must be at least one, unless the match was via sciname
                            name_to_vern[row[0]]=[row[1],[]]   
                    else:      #this is not preferred: no standard vernacular, save as an extra
                        name_to_vern[row[0]]=[None,[row[1]]]
                else:
                    #the entry exists, so we must have already filled out some vernaculars
                    if row[3] and len(name_to_vern[row[0]])==2: #another match, and standard vernacular didn't match: add to extras
                        name_to_vern[row[0]][1].append(row[1])
        for tab in results:
            for row in results[tab]:
                try:
                    ott=row[colname_map['ott']]
                    row.extend(ott_to_vern[ott])
                except KeyError:
                    try:
                        name=row[colname_map['name']]
                        row.extend(name_to_vern[name])
                    except:
                        pass #might reach here if the latin name has matched, but no vernaculars
        return {"headers":colname_map, "leaf_hits": results.get('ordered_leaves'), "node_hits": results.get('ordered_nodes'), "lang":language}    
    except:
        return {"headers":colname_map, "leaf_hits":[], "node_hits":[], "lang":language}

        
#find best vernacular name which matches user's query group by ott.
def findMatchMostName(vernacular_hits, searchFor):
    last_ott = -1
    temp_group = []
    vernacular_hit_res = []
    for row in vernacular_hits:
        if last_ott != row.ott:
            last_ott = row.ott
            if len(temp_group) > 0:
                vernacular_hit_res.append(findMatchMostNameInEachOttGroup(temp_group, searchFor))
            temp_group = []
        temp_group.append(row)
    if len(temp_group) > 0:
        vernacular_hit_res.append(findMatchMostNameInEachOttGroup(temp_group, searchFor))
    return vernacular_hit_res
    
def findMatchMostNameInEachOttGroup(group, searchFor):
    preferred_row = None
    preferred_vernacular = None
    
    for row in group:
        if row.preferred:
            preferred_row = row
            preferred_vernacular = row.vernacular
            if doesQueryMatchHit(searchFor, row.vernacular):
                return row                
    
    for row in group:
        if doesQueryMatchHit(searchFor, row.vernacular):
            unpreferred_hit = row.vernacular
            row.vernacular = preferred_vernacular
            row.unpreferred_hit = unpreferred_hit
            return row
                
    if preferred_row is None:
        return group[0]
    else:
        return preferred_row
        
def doesQueryMatchHit(query, hit):
    wordIndex = 0
    for word in query:
        wordIndex = wordIndex+1
        if word.upper() in hit.upper():
            if wordIndex == len(query):
                return True
        else:
            return False
    return False

def search_for_sponsor():
    """
    Searches OneZoom for sponsorship text

    :something?:`parameter1` And then describe the parameter.

    """
    response.headers["Access-Control-Allow-Origin"] = '*'
    try:
        searchFor = str(request.vars.query)
        #remove initial punctuation, e.g. we might have been passed in 
        searchType = request.vars.type or 'all'
        defaultImages = True if (request.vars.get('default_images')) else False
        order = True if (request.vars.get('sorted')) else False
        limit=request.vars.get('limit')
        start =request.vars.get('start') or 0
        return search_sponsor(searchFor, searchType, order, limit, start, defaultImages)
    except:
        raise
        return {}
        
def search_sponsor(searchFor, searchType, order_by_recent=None, limit=None, start=0, defaultImages=False):
    try:
        searchFor = searchFor.replace("%","").replace("_", " ").split(" ")
        verified_name = db.reservations.verified_name
        verified_more_info = db.reservations.verified_more_info
        colnames = ['OTT_ID', 'name', 'verified_name', 'verified_more_info', 'verified_kind', 'verified_url', 'verified_preferred_image']
        ##TO DO - should the alt_txt be translated somehow? How do we know the language asked for?
        alt_txt = {"verified_name":T("This leaf has been sponsored"),
                   "verified_more_info":T("text awaiting confirmation"),
                   "verified_url":None}
        colname_map = {nm:index for index,nm in enumerate(colnames)}
        search_query = None
        search_terms = []
        
        if searchType != "all":
            search_query = "verified_kind = " + db.placeholder
            search_terms.append(searchType)
            
        for word in ["%"+w+"%" for w in searchFor if w]:
            if search_query is None and searchType == "all":
                search_query = "(verified_name like " + db.placeholder + " or verified_more_info like " + db.placeholder + ")"
                search_terms.extend([word, word])
            elif search_query is None:
                search_query = "verified_name like " + db.placeholder
                search_terms.append(word)
            elif searchType == "all":
                search_query += " and " + "(verified_name like " + db.placeholder + " or verified_more_info like " + db.placeholder + ")"
                search_terms.extend([word, word])
            else:
                search_query += " and " + "verified_name like " + db.placeholder
                search_terms.append(word)
                
        query = "SELECT * FROM (SELECT "
        #a very complicated query here, use alternative text if this is not an active node (waiting verification or expired)
        query += ",".join(["IF(active,{0},{1}) as {0}".format(nm, "NULL" if alt_txt[nm] is None else ("'" + alt_txt[nm].replace("'","''") + "'")) if nm in alt_txt else nm for nm in colnames])
        query += " FROM (SELECT " + ",".join(colnames) + ",(DATE_ADD(verified_time, INTERVAL sponsorship_duration_days DAY) > CURDATE() AND verified_kind IS NOT NULL) AS active FROM reservations"
        query += " WHERE PP_transaction_code IS NOT NULL AND (deactivated IS NULL OR deactivated = '')"
        if order_by_recent:
            query += ' ORDER BY verified_time DESC'
        query += ") AS t1) as t2 WHERE " + search_query
        if limit:
            query += ' LIMIT ' + str(int(limit))
            if start:
                query += ' OFFSET ' + str(int(start))
        reservations = db.executesql(query, search_terms)
        
        reservationsOttArray = []
        for row in reservations:
            reservationsOttArray.append(row[colname_map['OTT_ID']])
            
        query = db.ordered_nodes.ott.belongs(reservationsOttArray)
        nodes = db(query).select(db.ordered_nodes.id, db.ordered_nodes.ott)
        
        query = db.ordered_leaves.ott.belongs(reservationsOttArray)
        leaves = db(query).select(db.ordered_leaves.id, db.ordered_leaves.ott)
    
        language=request.vars.lang or request.env.http_accept_language or 'en'
        common_names = get_common_names(reservationsOttArray, lang=language)
        
        if defaultImages:
            return {"common_names": common_names, "lang":language, "reservations": reservations, "nodes": nodes, "leaves": leaves, "headers": colname_map, "default_images":{row.ott:[row.src, row.src_id] for row in db(db.images_by_ott.ott.belongs(reservationsOttArray) & (db.images_by_ott.best_any == True)).select(db.images_by_ott.ott, db.images_by_ott.src, db.images_by_ott.src_id, orderby=~db.images_by_ott.src)} }
        else:
            return {"common_names": common_names, "lang":language, "reservations": reservations, "nodes": nodes, "leaves": leaves, "headers": colname_map}
        
    except:
        raise
        return {}

def get_ids_by_ott_array():
    """
    used e.g. to map an array of popular species to the leaf (or node) IDs
    also returns scinames if any (this is cheap to do)
    """
    session.forget(response)
    response.headers["Access-Control-Allow-Origin"] = '*'
    try:
        ottArray = [int(x) for x in request.vars.ott_array.split(",")]
        query = db.ordered_nodes.ott.belongs(ottArray)
        nodes = db(query).select(db.ordered_nodes.id, db.ordered_nodes.ott, db.ordered_nodes.name)
        query = db.ordered_leaves.ott.belongs(ottArray)
        leaves = db(query).select(db.ordered_leaves.id, db.ordered_leaves.ott, db.ordered_leaves.name)
        return {
            "nodes":  {n.ott:n.id for n in nodes},
            "leaves": {n.ott:n.id for n in leaves},
            "names":  dict([(n.ott,n.name) for n in nodes] + [(n.ott,n.name) for n in leaves])
        }
    except:
        return {"nodes": {}, "leaves": {}, "names": {}}

def otts2vns():
    """
    Used e.g. to fill out the popular species lists, and for Lifemap
    can call with request.vars.lang=XX and with oz_special=1
    Will return nulls for unmatched otts if return_nulls=1
    """
    session.forget(response)
    response.headers["Access-Control-Allow-Origin"] = '*'
    try:
        return get_common_names([int(x) for x in request.vars.otts.split(',')],
            return_nulls = True if request.vars.nulls else False,
            prefer_oz_special_names=True if request.vars.oz_special else False,
            include_unpreferred = True if (request.vars.include_unpreferred or request.vars.all) else False,
            return_all = True if request.vars.all else False,
            lang = request.vars.lang or request.env.http_accept_language or 'en')
    except AttributeError, ValueError:
        return {}
    
def update_visit_count():
    session.forget(response)
    response.headers["Access-Control-Allow-Origin"] = '*'
    try:
        if request.vars.api_hits:            
            values = []
            for ott in request.vars.api_hits.split(","):
                values.append("(" + ott + ",1,0,0)")
            values = ",\n".join(values)
            query = "insert into visit_count (ott, detail_fetch_count, search_count, leaf_click_count) values \n" + values + "\n"
            query = query + "on duplicate key update detail_fetch_count = detail_fetch_count + 1"
            db.executesql(query)
            
        if request.vars.search_hits:
            values = []
            for ott in request.vars.search_hits.split(","):
                values.append("(" + ott + ",0,1,0)")
            values = ",\n".join(values)
            query = "insert into visit_count (ott, detail_fetch_count, search_count, leaf_click_count) values \n" + values + "\n"
            query = query + "on duplicate key update search_count = search_count + 1"
            db.executesql(query)
            
        if request.vars.leaf_click_count:
            values = []
            for ott in request.vars.leaf_click_count.split(","):
                values.append("(" + ott + ",0,0,1)")
            values = ",\n".join(values)
            query = "insert into visit_count (ott, detail_fetch_count, search_count, leaf_click_count) values \n" + values + "\n"
            query = query + "on duplicate key update leaf_click_count = leaf_click_count + 1"
            db.executesql(query)
            
        return {"status":"success"}
    except:
        return {"status":"failure"}
    
    
def get_id_by_ott():
    session.forget(response)
    response.headers["Access-Control-Allow-Origin"] = '*'
    ott = request.vars.ott
    query = db.ordered_nodes.ott == ott
    result = db(query).select(db.ordered_nodes.id, db.ordered_nodes.ott)
    if len(result) > 0:
        return {"id": result[0].id}
    else:
        query = db.ordered_leaves.ott == ott
        result = db(query).select(db.ordered_leaves.id, db.ordered_leaves.ott)
        if len(result) > 0:
            return {"id": -result[0].id}
    return {"id": "none"}

#PRIVATE FUNCTIONS

#define a complicated global subbing Separators & Punctuation with a normal space
punctuation_to_space_table = {i:' ' for i in xrange(sys.maxunicode) \
                      if unicodedata.category(unichr(i)).startswith('Z') \
                      or (unicodedata.category(unichr(i)).startswith('P') \
                      and unichr(i) not in [u"'",u"’",u"-",u".",u"×", u"#"])} # allow e.g. ' in names
pinyinToneMarks = "".join({
    u'a': u'āáǎà', u'e': u'ēéěè', u'i': u'īíǐì',
    u'o': u'ōóǒò', u'u': u'ūúǔù', u'ü': u'ǖǘǚǜ',
    u'A': u'ĀÁǍÀ', u'E': u'ĒÉĚÈ', u'I': u'ĪÍǏÌ',
    u'O': u'ŌÓǑÒ', u'U': u'ŪÚǓÙ', u'Ü': u'ǕǗǙǛ'
}.values())

def punctuation_to_space(text):
    """
    Convert all space characters, and most punctuation, to normal spaces
    prior to separating search results into words
    """
    return text.translate(punctuation_to_space_table)

def is_logographic(word, lang_primary):
    """
    Identify if this search is for logographic (e.g. chinese) characters, in which case 
    we will not want to do a natural language search, and can search for each character 
    independently. Since there is no obvious way to identify logographic characters, we
    only do this if the search is for logographic languages, as described in
    https://en.wikipedia.org/wiki/List_of_writing_systems#Logographic_writing_systems
    which, restricted to extant languages, is only chinese, japanese, and korean
    """
    if lang_primary not in ["zh", "cnm", "ja", "ko"]:
        return False
    #if the word contains any ascii or accented ascii chars, it is not logographic (e.g. if chinese but searching for pinyin)
    return not any(ch in string.ascii_letters+string.digits+pinyinToneMarks for ch in word)

def acceptable_sciname(word):
    """
    the following regexp matches characters that are reasonable to accept in scientific name:
    [-./A-Za-z 0-9×αβγδμëüö{}*#]
    (this includes e.g. in bacterial strains etc). If we get a search word containing anything outside these characters, we can treat it as a vernacular name match
    """
    return all(ch in string.ascii_letters+string.digits+u" -./×αβγδμëüö{}*#" for ch in word) 
