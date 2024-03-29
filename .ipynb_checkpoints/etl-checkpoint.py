import configparser
from datetime import datetime
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, from_unixtime, concat,lit
from pyspark.sql.functions import year, month, dayofmonth, hour, weekofyear, date_format, to_timestamp
from pyspark.sql.types import DateType, TimestampType

config = configparser.ConfigParser()
config.read('dl.cfg')

os.environ['AWS_ACCESS_KEY_ID']=config['AWS']['AWS_ACCESS_KEY_ID']
os.environ['AWS_SECRET_ACCESS_KEY']=config['AWS']['AWS_SECRET_ACCESS_KEY']


def create_spark_session():
    
    ''' Creating of spark session: We config jars parkages with hadoop-aws version 2.7.0'''
    
    spark = SparkSession \
        .builder \
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:2.7.0") \
        .getOrCreate()
    return spark


def process_song_data(spark,input_data, output_data):
    
    ''' process_song_data function: this function extract informations from the song and create some dim table 

    spark: the spark context
    input_data: datasets source
    output_data: the directory that we will contains the parquet created
'''
    # get filepath to song data file
    song_data = input_data+"song_data/*/*/*/*.json"
    
    # read song data file
    df = spark.read.json(song_data)
    
    
    # extract columns to create songs table
    songs_table = df.select(['song_id','title','artist_id','year','duration'])
    
    # write songs table to parquet files partitioned by year and artist
    songs_table = songs_table.write.mode('overwrite')\
                             .partitionBy(['year','artist_id'])\
                             .parquet(output_data+"/songs.parquet")

    # extract columns to create artists table
    artists_table = df.select(['artist_id','artist_name','artist_location','artist_latitude','artist_longitude'])
    
    # write artists table to parquet files
    artists_table = artists_table.write.mode('overwrite')\
                                 .parquet(output_data+"/artists.parquet")


def process_log_data(spark, input_data, output_data):
    
    ''' process_log_data function: this function  read json files from input_data, extract informations and create some dim table and fact table
    
    spark: the spark context
    input_data: datasets source
    output_data: the directory that we will contains the parquet created
    '''

    # get filepath to log data file
    log_data = input_data+"log_data/*/*/*.json"
    
    # read log data file
    df = spark.read.json(log_data)
    
    # filter by actions for song plays
    df = df.filter(df.page=='NextSong')

    # extract columns for users table    
    users_table = df.select(['userId','firstName','lastName','gender','level'])
    
    # write users table to parquet files
    users_table = users_table.write.mode('overwrite')\
                             .parquet(output_data+"/users.parquet")

    
    df = df.withColumn('startime',from_unixtime(col('ts')/1000.0,"yyyy-MM-dd HH:mm:ss.SS"))
    df = df.withColumn('startime',to_timestamp("startime"))
 
    
    # extract columns to create time table
    time_table = df.select(['ts','startime', hour('startime').alias('hour'),\
                            dayofmonth('startime').alias('day'),month('startime').alias('month'),\
                            year('startime').alias('year') , weekofyear('startime').alias('week')])
    
    # write time table to parquet files partitioned by year and month
    time_table = time_table.write.mode('overwrite')\
                            .partitionBy(['year','month'])\
                            .parquet(output_data+"/times.parquet")

    # read in song data to use for songplays table
    song_df = spark.read.parquet(output_data+"/songs.parquet")

    # extract columns from joined song and log datasets to create songplays table 
    songplays_table = df.join(song_df, [(df.song == song_df.title),(df.length == song_df.duration)], how='inner')\
                        .select([concat('ts',lit('_'),'userId').alias('songplay_id'),'startime',\
                                 'userId','level','song_id','sessionId','location','userAgent'])

    songplays_table = songplays_table.withColumn('month',month(col('startime')))
    songplays_table = songplays_table.withColumn('year',year(col('startime')))
    
    # write songplays table to parquet files partitioned by year and month
    songplays_table = songplays_table.write.mode("overwrite")\
                                     .partitionBy(['month','year'])\
                                     .parquet(output_data+"/songplays.parquet")


def main():
    spark = create_spark_session()
    input_data = "s3a://udacity-dend/"
    output_data = "data/tables"
    
    process_song_data(spark, input_data, output_data)    
    process_log_data(spark, input_data, output_data)


if __name__ == "__main__":
    main()
