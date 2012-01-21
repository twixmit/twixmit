function twixmitMainReady(){
    window.saveResultsDom = $("#save-results");
    window.textToSave = $("#text-to-save");
    window.postResubmit = $("#checkbox-resubmit");
    window.postButton = $("button#post");
    
    window.yoursPendingList = $("ul#yours-pending");
    window.theirsPendingList = $("ul#theirs-pending");
    window.postBoxToClone = $("li#cloneme");
    
    $("form#post-form").unbind("submit");
    
    postButton.click(savePostForMix);
    
    loadYoursPending();
    setTimeout("loadTheirsPending()",500);
    
    setupPostLoadTimers();
    
    loadDemoPostsAll();
}

function setupPostLoadTimers(){
    setInterval("loadYoursPending()",30000);
    setInterval("loadTheirsPending()",30500);
}

function addPostToList(postBoxToClone, data_r_result, prependToList){
    var liDom = postBoxToClone.clone();
    liDom.children(".text").html(data_r_result.text);
    liDom.children(".time").text(data_r_result.created);
    liDom.children(".by").text("@" + data_r_result.by_user);
    liDom.children(".resubmit").text("resubmit? " + data_r_result.resubmit);
    liDom.attr("id",data_r_result.id)
    liDom.prependTo(prependToList);
    liDom.fadeIn('slow');
}

function loadPostsAll(which,cursorWindowKey,prependToList,noPostsText){
    var options = {
        dataType : "json",
        data : {"which" : which ,"since" : encodeURI(window[cursorWindowKey]) },
        success : function(data, textStatus, jqXHR){
            if (data.c != "None"){
                window[cursorWindowKey] = data.c;
            }
            
            if(data.r && data.r.length > 0){
                for( result in data.r){
                    
                    if (data.r[result].id && data.r[result].id != ""){
                        
                        var exists = $("li#" + data.r[result].id);
                        
                        if (exists && exists.length == 0){
                            addPostToList(postBoxToClone,data.r[result],prependToList);
                        } else {
                            if( console && console.warn){
                                console.warn("post already on page: %s",data.r[result].id )
                            }
                        }
                    } else {
                        if( console && console.warn){
                            console.warn("bad post result: %o",data.r[result])
                        }
                    }
                }
                
                if (prependToList.listView){
                    prependToList.listview('refresh');
                }
            }
                
            if(prependToList.children().length == 0){
                var liDom = postBoxToClone.clone();
                liDom.children(".text").text(noPostsText);
                liDom.show();
                liDom.prependTo(prependToList);
            }
        },
        error : function(jqXHR, textStatus, errorThrown){
            console.error(errorThrown);                  
        },
        url : "/getposts",
        type : "get"
    };
    
    $.ajax(options);

}

function addDemoPostToList(postBoxToClone, data_r_result, prependToList){
    var liDom = postBoxToClone.clone();
    liDom.children(".text").html("@" + data_r_result.to_user + " " + data_r_result.text);
    liDom.children(".time").text(data_r_result.created);
    liDom.children(".by").text("via @" + data_r_result.by_user);
    //liDom.children(".to").text("to @" + data_r_result.to_user);
    liDom.children(".link").html('<a href="' + data_r_result.link + '">' + data_r_result.link + '</a>');
    liDom.attr("id",data_r_result.id)
    liDom.prependTo(prependToList);
    liDom.fadeIn('slow');
}

function loadDemoPostsAll(){
    
    var postBoxToClone = $("#democloneme");
    var prependToList = $("#demo-posts");
    
    var options = {
        dataType : "json",
        data : {},
        success : function(data, textStatus, jqXHR){
        
            if(data.r && data.r.length > 0){
                for( result in data.r){
                    
                    if (data.r[result].id && data.r[result].id != ""){
                        
                        var exists = $("li#" + data.r[result].id);
                        
                        if (exists && exists.length == 0){
                            addDemoPostToList(postBoxToClone,data.r[result],prependToList);
                        } else {
                            if( console && console.warn){
                                console.warn("post already on page: %s",data.r[result].id )
                            }
                        }
                    } else {
                        if( console && console.warn){
                            console.warn("bad post result: %o",data.r[result])
                        }
                    }
                }
                
                if (prependToList.listView){
                    prependToList.listview('refresh');
                }
            }
                
            if(prependToList.children().length == 0){
                var liDom = postBoxToClone.clone();
                liDom.children(".text").text(noPostsText);
                liDom.show();
                liDom.prependTo(prependToList);
            }
        },
        error : function(jqXHR, textStatus, errorThrown){
            if (console && console.error){
                console.error(errorThrown);                  
            }
        },
        url : "/getdemoposts",
        type : "get"
    };
    
    $.ajax(options);

}

function loadYoursPending(){   
    loadPostsAll("yours-pending","yoursPendingListCursor",yoursPendingList,"You have no pending posts, share something!");
}

function loadTheirsPending(){
    loadPostsAll("theirs-pending","theirsPendingListCursor",theirsPendingList,"They have no pending posts, tell them to share something!");
}   

function formClientSideResultForListAdd(data){
    // TODO
}
    
function savePostForMix(e){
    var options = {
        dataType : "json",
        data : {"text" : textToSave.val(), "resubmit" : window.postResubmit.prop("checked") },
        success : function(data, textStatus, jqXHR){
                
            if (data && data.success == true){
                saveResultsDom.css("color","green").css("font-weight","bold");
                saveResultsDom.text("Saved!");
                textToSave.val("");
                
                formClientSideResultForListAdd(data);
                
            } else if (data){
                saveResultsDom.css("color","red").css("font-weight","bold");
                saveResultsDom.text(data.failure_message);
            } else {
                saveResultsDom.css("color","red").css("font-weight","bold");
                saveResultsDom.text(textStatus);
            }
        },
        error : function(jqXHR, textStatus, errorThrown){
                saveResultsDom.css("color","red").css("font-weight","bold");
                saveResultsDom.text(errorThrown);
        },
        url : "/saveformix",
        type : "post",
        beforeSend : function(jqXHR, settings){
            postButton.attr("disabled","disabled");
        },
        complete: function(jqXHR, textStatus){
            postButton.removeAttr("disabled");
        },
        cache : true
    };
    
    $.ajax(options);
}