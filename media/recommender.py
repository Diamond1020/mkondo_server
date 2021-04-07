import numpy as np
import pandas


class PopularityRecommender:
    def __init__(self):
        self.train_data = None
        self.user_id = None
        self.media_id = None
        self.popularity_recommendations = None
    
    def create(self, train_data, user_id, media_id):
        self.train_data = train_data
        self.user_id = user_id
        self.media_id = media_id

        # Get a count of user_ids for each unique song as recommendation score
        train_data_grouped = train_data.groupby([self.media_id]).agg({self.user_id: 'count'}).reset_index()
        train_data_grouped.rename(columns = {'user_id': 'score'},inplace=True)

        # Sort the songs based upon recommendation score
        train_data_sort = train_data_grouped.sort_values(['score', self.media_id], ascending = [0,1])

        # Generate a recommendation rank based upon score
        train_data_sort['Rank'] = train_data_sort['score'].rank(ascending=0, method='first')

        #Get the top 10 recommendations
        self.popularity_recommendations = train_data_sort.head(10)
    
    def recommend(self, user_id):
        user_recommendations = self.popularity_recommendations
        
        # Add user_id column for which the recommendations are being generated
        user_recommendations['user_id'] = user_id

        #Bring user_id column to the front
        cols = user_recommendations.columns.tolist()
        cols = cols[-1:] + cols[:-1]
        user_recommendations = user_recommendations[cols]
        
        return user_recommendations


class SimilarityRecommender:
    def __init__(self):
        self.train_data = None
        self.user_id = None
        self.media_id = None
        self.cooccurence_matrix = None
        self.media_dict = None
        self.rev_media_dict = None
        self.media_similarity_recommendations = None
    
    def create(self, train_data, user_id, media_id):
        """
        Create the item similarity based recommender system model
        """
        self.train_data = train_data
        self.user_id = user_id
        self.media_id = media_id
    
    def get_user_media(self, user_id):
        """
        Get unique media corresponding to a given user
        """
        user_data = self.train_data[self.train_data[self.user_id] == user_id]
        user_media = list(user_data[self.media_id].unique())
        
        return user_media

    def get_media_users(self, media_id):
        """
        Get unique users for a given media
        """
        media_data = self.train_data[self.train_data[self.media_id] == media_id]
        media_users = set(media_data[self.user_id].unique())
            
        return media_users

    def get_all_media_train_data(self):
        """
        Get unique media in the training data
        """
        all_media = list(self.train_data[self.media_id].unique())
            
        return all_media
    
    def construct_cooccurence_matrix(self, user_media, all_media):
        """
        Construct cooccurence matrix
        """
        
        # Get users for all media in user_media.
        user_media_users = []        
        for i in range(0, len(user_media)):
            user_media_users.append(self.get_media_users(user_media[i]))
            
        # Initialize the item cooccurence matrix of size 
        # len(user_media) X len(media)
        cooccurence_matrix = np.matrix(np.zeros(shape=(len(user_media), len(all_media))), float)
           
        # Calculate similarity between user media and all unique media
        # in the training data
        for i in range(0,len(all_media)):
            # Calculate unique listeners (users) of media (item) i
            media_i_data = self.train_data[self.train_data[self.media_id] == all_media[i]]
            users_i = set(media_i_data[self.user_id].unique())
            
            for j in range(0,len(user_media)):       
                    
                # Get unique listeners (users) of media (item) j
                users_j = user_media_users[j]
                    
                # Calculate intersection of listeners of songs i and j
                users_intersection = users_i.intersection(users_j)
                
                #Calculate cooccurence_matrix[i,j] as Jaccard Index
                if len(users_intersection) != 0:
                    #Calculate union of listeners of songs i and j
                    users_union = users_i.union(users_j)
                    
                    cooccurence_matrix[j,i] = float(len(users_intersection))/float(len(users_union))
                else:
                    cooccurence_matrix[j,i] = 0
                    
        
        return cooccurence_matrix
    
    def generate_top_recommendations(self, user, cooccurence_matrix, all_media, user_media):
        """
        Use the cooccurence matrix to make top recommendations
        """
        print("Non zero values in cooccurence_matrix :%d" % np.count_nonzero(cooccurence_matrix))
        
        # Calculate a weighted average of the scores in cooccurence matrix for all user songs.
        user_sim_scores = cooccurence_matrix.sum(axis=0)/float(cooccurence_matrix.shape[0])
        user_sim_scores = np.array(user_sim_scores)[0].tolist()
 
        # Sort the indices of user_sim_scores based upon their value
        # Also maintain the corresponding score
        sort_index = sorted(((e,i) for i,e in enumerate(list(user_sim_scores))), reverse=True)
    
        # Create a dataframe from the following
        columns = ['user_id', 'media_id_y', 'score', 'rank']
        # index = np.arange(1) # array of numbers for the number of samples
        df = pandas.DataFrame(columns=columns)
         
        # Fill the dataframe with top 10 item based recommendations
        rank = 1 
        for i in range(0,len(sort_index)):
            if ~np.isnan(sort_index[i][0]) and all_media[sort_index[i][1]] not in user_media and rank <= 10:
                df.loc[len(df)]=[user,all_media[sort_index[i][1]],sort_index[i][0],rank]
                rank = rank+1
        
        # Handle the case where there are no recommendations
        if df.shape[0] == 0:
            print("The current user has no songs for training the item similarity based recommendation model.")
            return -1
        else:
            return df
    
    def recommend(self, user):
        """
        Use the item similarity based recommender system model to 
        make recommendations
        """
        
        # Get all unique songs for this user
        user_media = self.get_user_media(user)    
            
        print("No. of unique songs for the user: %d" % len(user_media))
        
        # Get all unique items (songs) in the training data
        all_media = self.get_all_media_train_data()
        
        print("no. of unique songs in the training set: %d" % len(all_media))
         
        # Construct item cooccurence matrix of size 
        # len(user_songs) X len(songs)
        cooccurence_matrix = self.construct_cooccurence_matrix(user_media, all_media)
        
        # Use the cooccurence matrix to make recommendations
        df_recommendations = self.generate_top_recommendations(user, cooccurence_matrix, all_media, user_media)
                
        return df_recommendations

    def get_similar_items(self, media_list):
        """
        Get similar items to given items
        """
        user_media = media_list
        
        # Get all unique items (media) in the training data
        all_media = self.get_all_media_train_data()
        
        print("no. of unique songs in the training set: %d" % len(all_media))
         
        # Construct item cooccurence matrix of size 
        # len(user_songs) X len(songs)
        cooccurence_matrix = self.construct_cooccurence_matrix(user_media, all_media)
        
        # Use the cooccurence matrix to make recommendations
        user = ""
        df_recommendations = self.generate_top_recommendations(user, cooccurence_matrix, all_media, user_media)
         
        return df_recommendations
